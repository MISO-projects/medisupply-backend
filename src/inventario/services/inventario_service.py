from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from fastapi import Depends, HTTPException
from http import HTTPStatus
from datetime import datetime, timezone, date
import logging
import httpx
import os
from sqlalchemy import func, and_, or_, nullslast
import json
from uuid import UUID

from db.database import get_db
from db.inventario_model import Inventario
from schemas.inventario_schema import CrearRegistroInventarioSchema, CrearRegistroPedidoSchema
from db.redis_client import get_redis_client
from services.pubsub_service import get_pubsub_service

logger = logging.getLogger(__name__)


class InventarioService:
    CACHE_TTL_PROVEEDOR = 3600  # 1 hour for individual provider
    CACHE_TTL_LIST = 300  # 5 minutes for lists
    CACHE_TTL_COUNT = 300  # 5 minutes for counts

    def __init__(self, db: Session = Depends(get_db)):
        self.db = db
        self.redis_client = get_redis_client()
        self.pubsub_service = get_pubsub_service()
        self.productos_service_url = os.getenv(
            "PRODUCTOS_SERVICE_URL", "http://productos-service:3000"
        )

    
    def _get_cache(self, key: str) -> Optional[Any]:
        """Get data from cache"""
        try:
            if self.redis_client is None:
                return None
            cached_data = self.redis_client.get(key)
            if cached_data:
                return json.loads(cached_data)
            return None
        except Exception as e:
            logger.warning(f"Error getting cache for key {key}: {e}")
            return None

    def _set_cache(self, key: str, value: Any, ttl: int) -> None:
        """Set data in cache"""
        try:
            if self.redis_client is None:
                return
            self.redis_client.setex(key, ttl, json.dumps(value, default=str))
        except Exception as e:
            logger.warning(f"Error setting cache for key {key}: {e}")

    def _delete_cache(self, pattern: str) -> None:
        """Delete cache keys matching pattern"""
        try:
            if self.redis_client is None:
                return
            keys = self.redis_client.keys(pattern)
            if keys:
                self.redis_client.delete(*keys)
        except Exception as e:
            logger.warning(f"Error deleting cache for pattern {pattern}: {e}")

    def _invalidate_inventario_caches(self, inventario_id: Optional[str] = None) -> None:
        """Invalidate all inventario-related caches"""
        try:
            if inventario_id:
                self._delete_cache(f"inventario:{inventario_id}")
            # Invalidate list and count caches
            self._delete_cache("inventario:list:*")
            self._delete_cache("inventario:count:*")
        except Exception as e:
            logger.warning(f"Error invalidating caches: {e}")

    async def _get_detalles_productos(self, producto_ids: List[str]) -> Dict[str, Any]:
        """
        Obtiene detalles de productos para una lista de IDs.
        Retorna un diccionario con campos como: nombre, sku, categoria, unidad_medida,
        tipo_almacenamiento, precio_unitario, descripcion, imagen_url.
        """
        if not producto_ids:
            return {}
        
        unique_ids = list(set(producto_ids))
        
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(
                    f"{self.productos_service_url}/api/productos/batch-details",
                    json={"producto_ids": unique_ids}
                )
                
                if response.status_code == 200:
                    data = response.json()
                    # Retorna el mapa: {"uuid-1": {"nombre": "...", "sku": "..."}}
                    return data.get("detalles", {}) 
                else:
                    logger.error(f"Error al obtener detalles de productos: {response.status_code} - {response.text}")
                    return {}
                    
        except httpx.RequestError as e:
            logger.error(f"Error de conexión al servicio de productos: {e}")
            return {}

    async def _get_producto_ids_by_filters(
        self,
        text_search: Optional[str] = None,
        categoria: Optional[str] = None
    ) -> List[str]:
        """
        Obtiene IDs de productos que coinciden con los filtros proporcionados
        llamando al servicio de productos.
        """
        # Si no hay filtros de producto, retornar lista vacía (significa que no se filtra por producto)
        if not text_search and not categoria:
            return []

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(
                    f"{self.productos_service_url}/api/productos/filter-ids",
                    json={
                        "text_search": text_search,
                        "categoria": categoria
                    }
                )

                if response.status_code == 200:
                    data = response.json()
                    producto_ids = data.get("producto_ids", [])
                    logger.info(f"Se obtuvieron {len(producto_ids)} IDs de productos que coinciden con los filtros")
                    return producto_ids
                else:
                    logger.error(f"Error al obtener IDs de productos por filtros: {response.status_code} - {response.text}")
                    return []

        except httpx.RequestError as e:
            logger.error(f"Error de conexión al servicio de productos para filtros: {e}")
            return []


    async def crear_registro_inventario(self, inventario_data: CrearRegistroInventarioSchema) -> Dict[str, Any]:
        """
        Crea un nuevo registro de inventario en el sistema.
        
        Args:
            inventario_data: Datos del registro de inventario a crear
            
        Returns:
            Dict con los datos del registro de inventario creado
            
        Raises:
            HTTPException: Si ocurre un error durante la creación
        """
        try:
            nuevo_inventario = Inventario(
                producto_id=inventario_data.producto_id,
                lote=inventario_data.lote,
                fecha_vencimiento=inventario_data.fecha_vencimiento,
                cantidad=inventario_data.cantidad,
                ubicacion=inventario_data.ubicacion,
                temperatura_requerida=inventario_data.temperatura_requerida,
                estado=inventario_data.estado,
                condiciones_especiales=inventario_data.condiciones_especiales,
                observaciones=inventario_data.observaciones,
            )
            self.db.add(nuevo_inventario)
            self.db.commit()
            self.db.refresh(nuevo_inventario)
            self._invalidate_inventario_caches()

            # Publicar evento a auditoría
            await self._publicar_evento_inventario(
                operation="CREAR",
                inventario_id=str(nuevo_inventario.id),
                producto_id=str(nuevo_inventario.producto_id),
                datos={
                    "lote": nuevo_inventario.lote,
                    "cantidad": nuevo_inventario.cantidad,
                    "ubicacion": nuevo_inventario.ubicacion,
                    "estado": nuevo_inventario.estado,
                    "fecha_vencimiento": nuevo_inventario.fecha_vencimiento.isoformat() if nuevo_inventario.fecha_vencimiento else None
                }
            )

            await self._notificar_actualizacion_a_productos()
            return nuevo_inventario.to_dict()
        except IntegrityError as ie:
            self.db.rollback()
            logger.error(f"Integrity error creating inventario: {ie}")
            raise HTTPException(
                status_code=HTTPStatus.CONFLICT,
                detail="Error de integridad al crear el registro de inventario."
            )
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error creating inventario: {e}")
            raise HTTPException(
                status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
                detail="Error interno al crear el registro de inventario."
            )

    async def listar_registros_paginados(
        self,
        skip: int,
        limit: int,
        text_search: Optional[str] = None,
        categoria: Optional[str] = None,
        estado: Optional[str] = None
    ) -> tuple[List[Dict[str, Any]], int]:
        """
        Obtiene una lista paginada de registros de inventario con filtros opcionales.
        Siempre enriquece los registros con nombre y SKU del producto.

        Args:
            text_search: Busca en producto nombre, producto sku, o inventario ubicacion
            categoria: Filtra productos por categoría
            estado: Filtra inventario por estado
        """
        try:
            # Generar clave de caché basada en los filtros
            cache_key = f"inventario:list:{text_search or 'all'}:{categoria or 'all'}:{estado or 'all'}:{skip}:{limit}"
            cached_data = self._get_cache(cache_key)

            if cached_data is not None:
                logger.debug(f"Cache hit for inventario list")
                return cached_data.get('items', []), cached_data.get('total', 0)

            logger.debug(f"Cache miss for inventario list")

            query = self.db.query(Inventario)

            # Aplicar filtros de producto: obtener IDs de productos que coinciden
            producto_ids_filtrados = []
            if text_search or categoria:
                producto_ids_filtrados = await self._get_producto_ids_by_filters(
                    text_search=text_search,
                    categoria=categoria
                )

            # Aplicar filtros combinados: producto_id OR ubicacion (si text_search)
            if text_search:
                filters_list = []

                # Si hay productos que coinciden, agregar filtro por producto_id
                if producto_ids_filtrados:
                    producto_uuids = [UUID(pid) for pid in producto_ids_filtrados]
                    filters_list.append(Inventario.producto_id.in_(producto_uuids))

                # Agregar filtro por ubicacion
                filters_list.append(Inventario.ubicacion.ilike(f"%{text_search}%"))

                # Aplicar OR entre producto_id y ubicacion
                # Si solo hay un filtro, aplicarlo directamente; si hay múltiples, usar or_()
                if len(filters_list) == 1:
                    query = query.filter(filters_list[0])
                elif len(filters_list) > 1:
                    query = query.filter(or_(*filters_list))
            elif categoria:
                # Solo filtro por categoria (sin text_search)
                if producto_ids_filtrados:
                    producto_uuids = [UUID(pid) for pid in producto_ids_filtrados]
                    query = query.filter(Inventario.producto_id.in_(producto_uuids))
                else:
                    # Si categoria no encontró productos, retornar vacío
                    return [], 0

            # Aplicar filtros de inventario
            if estado:
                query = query.filter(Inventario.estado == estado)

            # Contar total después de aplicar filtros
            total = query.count()
            
            # Aplicar ordenamiento y paginación
            registros_db = query.order_by(Inventario.fecha_recepcion.desc()) \
                                .offset(skip).limit(limit).all()

            if not registros_db:
                return [], 0
            
            producto_ids = [str(r.producto_id) for r in registros_db]
            detalles_map = await self._get_detalles_productos(producto_ids)
            items_enriquecidos = []
            for registro in registros_db:
                registro_dict = registro.to_dict()
                detalles = detalles_map.get(str(registro.producto_id), {})
                registro_dict["producto_nombre"] = detalles.get("nombre", "Producto no encontrado")
                registro_dict["producto_sku"] = detalles.get("sku", "N/A")
                registro_dict["producto_categoria"] = detalles.get("categoria")
                registro_dict["producto_unidad_medida"] = detalles.get("unidad_medida")
                registro_dict["producto_tipo_almacenamiento"] = detalles.get("tipo_almacenamiento")
                registro_dict["producto_precio_unitario"] = detalles.get("precio_unitario")
                registro_dict["producto_descripcion"] = detalles.get("descripcion")
                registro_dict["producto_imagen_url"] = detalles.get("imagen_url")

                items_enriquecidos.append(registro_dict)

            # Guardar en caché
            cache_data = {
                'items': items_enriquecidos,
                'total': total
            }
            self._set_cache(cache_key, cache_data, self.CACHE_TTL_LIST)

            return items_enriquecidos, total

        except Exception as e:
            logger.error(f"Error al listar registros de inventario paginados: {e}")
            raise HTTPException(
                status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
                detail="Error interno al listar los registros de inventario."
            )
        
    def get_stock_agregado_por_ids(self, producto_ids: List[str]) -> Dict[str, int]:
        """
        Obtiene el stock agregado total para una lista de IDs de productos.
        Suma la 'cantidad' de todos los registros que:
        1. Tienen estado 'DISPONIBLE'.
        2. No están vencidos (fecha_vencimiento > hoy).
        """
        try:
            if not producto_ids:
                return {}
            
            today = date.today()
            
            query = self.db.query(
                Inventario.producto_id,
                func.sum(Inventario.cantidad).label("stock_total")
            ).filter(
                Inventario.producto_id.in_(producto_ids),
                Inventario.estado == 'DISPONIBLE',
                or_(
                    Inventario.fecha_vencimiento.is_(None),
                    Inventario.fecha_vencimiento > today
                )
            ).group_by(
                Inventario.producto_id
            )
            
            resultados = query.all()
            stock_map = {str(producto_id): total_stock for producto_id, total_stock in resultados}
            
            response_data = {pid: stock_map.get(pid, 0) for pid in producto_ids}
            
            logger.info(f"Stock agregado consultado para {len(producto_ids)} productos.")
            return response_data
        except Exception as e:
            logger.error(f"Error al obtener stock agregado: {e}")
            return {pid: 0 for pid in producto_ids}
    
    

    def listar_stock_disponible(self) -> List[Dict[str, Any]]:
        """
        Lista todos los registros de inventario que tienen cantidad > 0.
        Excluye los registros con estado que no sea DISPONIBLE o RESERVADO.
        """
        try:
            # Consulta para filtrar registros donde la cantidad sea mayor que 0
            registros_db = self.db.query(Inventario).filter(
                Inventario.cantidad > 0,
                # Inventario.estado.in_(['DISPONIBLE', 'RESERVADO'])
            ).all()

            stock_list = [registro.to_dict() for registro in registros_db]
            
            logger.info(f"Se encontraron {len(stock_list)} registros con stock disponible.")
            return stock_list

        except Exception as e:
            logger.error(f"Error al listar stock disponible: {e}")
            raise HTTPException(
                status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
                detail="Error interno al listar el stock de inventario."
            )
    
    async def _notificar_actualizacion_a_productos(self):
        """
        Avisa a productos-service (usando el webhook)
        que debe limpiar su caché de listas.
        """
        PRODUCTOS_SERVICE_URL = self.productos_service_url 
        try:
            async with httpx.AsyncClient() as client:
                await client.post(
                    f"{PRODUCTOS_SERVICE_URL}/api/productos/internal/cache/invalidate-lists"
                )
            logger.info("Notificación de invalidación de caché enviada a productos.")
        except Exception as e:
            logger.warning(f"No se pudo notificar a productos-service: {e}")

    async def disminuir_stock_por_pedido(self, data: CrearRegistroPedidoSchema) -> Dict[str, Any]:
        """
        Disminuye el stock de un producto basado en una solicitud de pedido (FIFO/FEFO).

        La lógica sigue un orden estricto de prioridad:
        1. Lotes con fecha_vencimiento más próxima (no vencidos).
        2. Lotes sin fecha_vencimiento, por fecha_recepcion más antigua.
        
        Solo se consideran lotes DISPONIBLES, con cantidad > 0 y no vencidos.
        Esta operación es transaccional y usa FOR UPDATE para evitar race conditions.
        """
        
        if not data.producto_id:
            raise HTTPException(
                status_code=HTTPStatus.BAD_REQUEST,
                detail="El 'producto_id' es requerido."
            )

        cantidad_a_disminuir = data.cantidad_producto_solicitada
        producto_id = data.producto_id
        
        try:
            today = date.today()
            
            lotes_disponibles = self.db.query(Inventario).filter(
                Inventario.producto_id == producto_id,
                Inventario.estado == 'DISPONIBLE',
                Inventario.cantidad > 0,
                or_(
                    Inventario.fecha_vencimiento.is_(None),
                    Inventario.fecha_vencimiento > today # No vencidos
                )
            ).order_by(
                nullslast(Inventario.fecha_vencimiento.asc()) 
            ).order_by(
                Inventario.fecha_recepcion.asc() 
            ).with_for_update().all()

            total_stock_disponible = sum(lote.cantidad for lote in lotes_disponibles)

            if total_stock_disponible < cantidad_a_disminuir:
                self.db.rollback() 
                raise HTTPException(
                    status_code=HTTPStatus.BAD_REQUEST, 
                    detail=f"Stock insuficiente para {producto_id}. Solicitado: {cantidad_a_disminuir}, Disponible: {total_stock_disponible}"
                )

           
            cantidad_restante_por_disminuir = cantidad_a_disminuir
            lotes_afectados_info = [] 

            for lote in lotes_disponibles:
                if cantidad_restante_por_disminuir <= 0:
                    break 

                cantidad_disminuida_de_este_lote = 0
                
                if lote.cantidad >= cantidad_restante_por_disminuir:
                    cantidad_disminuida_de_este_lote = cantidad_restante_por_disminuir
                    lote.cantidad -= cantidad_restante_por_disminuir
                    cantidad_restante_por_disminuir = 0
                else:
                    cantidad_disminuida_de_este_lote = lote.cantidad
                    cantidad_restante_por_disminuir -= lote.cantidad
                    lote.cantidad = 0
                    lote.estado = 'AGOTADO'
                
                lotes_afectados_info.append({
                    "id": lote.id, 
                    "lote": lote.lote,
                    "cantidad_disminuida": cantidad_disminuida_de_este_lote,
                    "cantidad_restante_lote": lote.cantidad
                })
            
            self.db.commit()
            self._invalidate_inventario_caches()

            # Publicar evento a auditoría
            await self._publicar_evento_inventario(
                operation="DISMINUIR",
                inventario_id=str(lotes_disponibles[0].id) if lotes_disponibles else None,
                producto_id=str(producto_id),
                datos={
                    "cantidad_disminuida": cantidad_a_disminuir,
                    "stock_restante": total_stock_disponible - cantidad_a_disminuir,
                    "lotes_afectados": len(lotes_afectados_info)
                },
                cambios={
                    "cantidad_anterior": total_stock_disponible,
                    "cantidad_nueva": total_stock_disponible - cantidad_a_disminuir
                }
            )

            await self._notificar_actualizacion_a_productos()

            logger.info(f"Stock disminuido exitosamente para {producto_id}. Cantidad: {cantidad_a_disminuir}")
            
            return {
                "producto_id": str(producto_id),
                "cantidad_disminuida": cantidad_a_disminuir,
                "stock_restante_total": total_stock_disponible - cantidad_a_disminuir,
                "lotes_afectados": lotes_afectados_info
            }
            
        except HTTPException:
            self.db.rollback()
            raise
        except IntegrityError as ie:
            self.db.rollback()
            logger.error(f"Integrity error updating register inventario: {ie}")
            raise HTTPException(
                status_code=HTTPStatus.CONFLICT,
                detail="Error de integridad al actualizar el inventario."
            )
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error al disminuir stock: {e}")
            raise HTTPException(
                status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
                detail="Error interno al editar el registro de inventario."
            )

    async def _publicar_evento_inventario(
        self,
        operation: str,
        inventario_id: Optional[str] = None,
        producto_id: Optional[str] = None,
        usuario_id: Optional[str] = None,
        ip_origen: Optional[str] = None,
        datos: Optional[Dict[str, Any]] = None,
        cambios: Optional[Dict[str, Any]] = None
    ):
        """
        Publica un evento de inventario a Pub/Sub para ser procesado por auditoría.

        Args:
            operation: Tipo de operación (CREAR, MODIFICAR, ELIMINAR, DISMINUIR)
            inventario_id: UUID del registro de inventario
            producto_id: UUID del producto
            usuario_id: UUID del usuario que realizó la operación
            ip_origen: IP desde donde se realizó la operación
            datos: Datos relevantes de la operación
            cambios: Cambios realizados (antes/después)
        """
        try:
            evento = {
                "event_type": "inventory_operation",
                "operation": operation,
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "inventario_id": inventario_id,
                "producto_id": producto_id,
                "usuario_id": usuario_id,
                "ip_origen": ip_origen,
                "datos": datos or {},
                "cambios": cambios
            }

            success = self.pubsub_service.publish_event(evento)

            if success:
                logger.info(f"Evento de inventario publicado: {operation} - {inventario_id}")
            else:
                logger.warning(f"No se pudo publicar evento de inventario: {operation}")

        except Exception as e:
            # No lanzar excepción para que no afecte la operación principal
            logger.error(f"Error publicando evento de inventario: {e}", exc_info=True)


def get_inventario_service(db: Session = Depends(get_db)) -> InventarioService:
    """
    Función de dependencia para obtener una instancia del servicio de inventario.
    """
    return InventarioService(db)

