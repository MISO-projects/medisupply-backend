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
import sys

# Importar modelo de auditoría
sys.path.append(os.path.join(os.path.dirname(__file__), '../..'))
from auditoria.db.models import AuditLog

from db.database import get_db
from db.inventario_model import Inventario
from schemas.inventario_schema import CrearRegistroInventarioSchema, CrearRegistroPedidoSchema, ActualizarInventarioSchema
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


    async def crear_registro_inventario(
        self, 
        inventario_data: CrearRegistroInventarioSchema,
        usuario_id: Optional[str] = None,
        ip_origen: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Crea un nuevo registro de inventario en el sistema.
        Registra la operación en auditoría de forma atómica.
        
        Args:
            inventario_data: Datos del registro de inventario a crear
            usuario_id: UUID del usuario que realiza la operación
            ip_origen: IP desde donde se realiza la operación
            
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
            self.db.flush()  # Para obtener el ID sin hacer commit todavía

            # Registrar en auditoría (misma transacción)
            audit_log = AuditLog(
                event_type="inventory_operation",
                operation="CREAR",
                inventario_id=nuevo_inventario.id,
                producto_id=nuevo_inventario.producto_id,
                usuario_id=UUID(usuario_id) if usuario_id else None,
                ip_origen=ip_origen,
                datos_operacion={
                    "lote": nuevo_inventario.lote,
                    "cantidad": nuevo_inventario.cantidad,
                    "ubicacion": nuevo_inventario.ubicacion,
                    "estado": nuevo_inventario.estado,
                    "fecha_vencimiento": nuevo_inventario.fecha_vencimiento.isoformat() if nuevo_inventario.fecha_vencimiento else None
                },
                cambios=None,
                timestamp=datetime.now(timezone.utc)
            )
            self.db.add(audit_log)
            
            # Commit único para ambas operaciones
            self.db.commit()
            self.db.refresh(nuevo_inventario)
            self._invalidate_inventario_caches()

            await self._notificar_actualizacion_a_productos()
            logger.info(f"Inventario creado: {nuevo_inventario.id} por usuario: {usuario_id}")
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

    async def disminuir_stock_por_pedido(
        self, 
        data: CrearRegistroPedidoSchema,
        usuario_id: Optional[str] = None,
        ip_origen: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Disminuye el stock de un producto basado en una solicitud de pedido (FIFO/FEFO).
        Registra la operación en auditoría de forma atómica.

        La lógica sigue un orden estricto de prioridad:
        1. Lotes con fecha_vencimiento más próxima (no vencidos).
        2. Lotes sin fecha_vencimiento, por fecha_recepcion más antigua.
        
        Solo se consideran lotes DISPONIBLES, con cantidad > 0 y no vencidos.
        Esta operación es transaccional y usa FOR UPDATE para evitar race conditions.
        
        Args:
            data: Datos de la solicitud de pedido
            usuario_id: UUID del usuario que realiza la operación
            ip_origen: IP desde donde se realiza la operación
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
            
            # Registrar en auditoría (misma transacción)
            audit_log = AuditLog(
                event_type="inventory_operation",
                operation="DISMINUIR",
                inventario_id=lotes_disponibles[0].id if lotes_disponibles else None,
                producto_id=UUID(producto_id) if isinstance(producto_id, str) else producto_id,
                usuario_id=UUID(usuario_id) if usuario_id else None,
                ip_origen=ip_origen,
                datos_operacion={
                    "cantidad_disminuida": cantidad_a_disminuir,
                    "stock_restante": total_stock_disponible - cantidad_a_disminuir,
                    "lotes_afectados": len(lotes_afectados_info),
                    "detalles_lotes": lotes_afectados_info
                },
                cambios={
                    "cantidad_anterior": total_stock_disponible,
                    "cantidad_nueva": total_stock_disponible - cantidad_a_disminuir
                },
                timestamp=datetime.now(timezone.utc)
            )
            self.db.add(audit_log)
            
            # Commit único para ambas operaciones
            self.db.commit()
            self._invalidate_inventario_caches()

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

    async def actualizar_registro_inventario(
        self,
        inventario_id: str,
        datos_actualizacion: ActualizarInventarioSchema,
        usuario_id: Optional[str] = None,
        ip_origen: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Actualiza un registro de inventario existente.
        Registra la operación en auditoría de forma atómica, incluyendo valores anteriores y nuevos.
        
        Args:
            inventario_id: UUID del registro a actualizar
            datos_actualizacion: Datos a actualizar
            usuario_id: UUID del usuario que realiza la operación
            ip_origen: IP desde donde se realiza la operación
            
        Returns:
            Dict con los datos del registro actualizado
            
        Raises:
            HTTPException: Si el registro no existe o hay un error
        """
        try:
            # Buscar el registro
            inventario = self.db.query(Inventario).filter(
                Inventario.id == UUID(inventario_id)
            ).first()
            
            if not inventario:
                raise HTTPException(
                    status_code=HTTPStatus.NOT_FOUND,
                    detail=f"Registro de inventario {inventario_id} no encontrado"
                )
            
            # Guardar valores anteriores para auditoría
            valores_anteriores = {
                "lote": inventario.lote,
                "fecha_vencimiento": inventario.fecha_vencimiento.isoformat() if inventario.fecha_vencimiento else None,
                "cantidad": inventario.cantidad,
                "ubicacion": inventario.ubicacion,
                "temperatura_requerida": inventario.temperatura_requerida,
                "estado": inventario.estado,
                "condiciones_especiales": inventario.condiciones_especiales,
                "observaciones": inventario.observaciones
            }
            
            # Aplicar cambios
            cambios_realizados = {}
            if datos_actualizacion.lote is not None:
                inventario.lote = datos_actualizacion.lote
                cambios_realizados["lote"] = {"anterior": valores_anteriores["lote"], "nuevo": datos_actualizacion.lote}
            
            if datos_actualizacion.fecha_vencimiento is not None:
                inventario.fecha_vencimiento = datos_actualizacion.fecha_vencimiento
                cambios_realizados["fecha_vencimiento"] = {
                    "anterior": valores_anteriores["fecha_vencimiento"],
                    "nuevo": datos_actualizacion.fecha_vencimiento.isoformat()
                }
            
            if datos_actualizacion.cantidad is not None:
                inventario.cantidad = datos_actualizacion.cantidad
                cambios_realizados["cantidad"] = {"anterior": valores_anteriores["cantidad"], "nuevo": datos_actualizacion.cantidad}
            
            if datos_actualizacion.ubicacion is not None:
                inventario.ubicacion = datos_actualizacion.ubicacion
                cambios_realizados["ubicacion"] = {"anterior": valores_anteriores["ubicacion"], "nuevo": datos_actualizacion.ubicacion}
            
            if datos_actualizacion.temperatura_requerida is not None:
                inventario.temperatura_requerida = datos_actualizacion.temperatura_requerida
                cambios_realizados["temperatura_requerida"] = {
                    "anterior": valores_anteriores["temperatura_requerida"],
                    "nuevo": datos_actualizacion.temperatura_requerida
                }
            
            if datos_actualizacion.estado is not None:
                inventario.estado = datos_actualizacion.estado
                cambios_realizados["estado"] = {"anterior": valores_anteriores["estado"], "nuevo": datos_actualizacion.estado}
            
            if datos_actualizacion.condiciones_especiales is not None:
                inventario.condiciones_especiales = datos_actualizacion.condiciones_especiales
                cambios_realizados["condiciones_especiales"] = {
                    "anterior": valores_anteriores["condiciones_especiales"],
                    "nuevo": datos_actualizacion.condiciones_especiales
                }
            
            if datos_actualizacion.observaciones is not None:
                inventario.observaciones = datos_actualizacion.observaciones
                cambios_realizados["observaciones"] = {
                    "anterior": valores_anteriores["observaciones"],
                    "nuevo": datos_actualizacion.observaciones
                }
            
            # Registrar en auditoría (misma transacción)
            audit_log = AuditLog(
                event_type="inventory_operation",
                operation="MODIFICAR",
                inventario_id=inventario.id,
                producto_id=inventario.producto_id,
                usuario_id=UUID(usuario_id) if usuario_id else None,
                ip_origen=ip_origen,
                datos_operacion={
                    "campos_modificados": list(cambios_realizados.keys()),
                    "total_cambios": len(cambios_realizados)
                },
                cambios=cambios_realizados,
                timestamp=datetime.now(timezone.utc)
            )
            self.db.add(audit_log)
            
            # Commit único para ambas operaciones
            self.db.commit()
            self.db.refresh(inventario)
            self._invalidate_inventario_caches(str(inventario.id))
            
            await self._notificar_actualizacion_a_productos()
            logger.info(f"Inventario actualizado: {inventario_id} por usuario: {usuario_id}")
            return inventario.to_dict()
            
        except HTTPException:
            raise
        except IntegrityError as ie:
            self.db.rollback()
            logger.error(f"Integrity error updating inventario: {ie}")
            raise HTTPException(
                status_code=HTTPStatus.CONFLICT,
                detail="Error de integridad al actualizar el registro de inventario."
            )
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error updating inventario: {e}")
            raise HTTPException(
                status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
                detail="Error interno al actualizar el registro de inventario."
            )

    async def eliminar_registro_inventario(
        self,
        inventario_id: str,
        usuario_id: Optional[str] = None,
        ip_origen: Optional[str] = None
    ) -> Dict[str, str]:
        """
        Elimina un registro de inventario.
        Registra la operación en auditoría de forma atómica, guardando todos los datos del registro eliminado.
        
        Args:
            inventario_id: UUID del registro a eliminar
            usuario_id: UUID del usuario que realiza la operación
            ip_origen: IP desde donde se realiza la operación
            
        Returns:
            Dict con mensaje de confirmación
            
        Raises:
            HTTPException: Si el registro no existe o hay un error
        """
        try:
            # Buscar el registro
            inventario = self.db.query(Inventario).filter(
                Inventario.id == UUID(inventario_id)
            ).first()
            
            if not inventario:
                raise HTTPException(
                    status_code=HTTPStatus.NOT_FOUND,
                    detail=f"Registro de inventario {inventario_id} no encontrado"
                )
            
            # Guardar todos los datos para auditoría antes de eliminar
            datos_eliminados = {
                "id": str(inventario.id),
                "producto_id": str(inventario.producto_id),
                "lote": inventario.lote,
                "fecha_vencimiento": inventario.fecha_vencimiento.isoformat() if inventario.fecha_vencimiento else None,
                "cantidad": inventario.cantidad,
                "ubicacion": inventario.ubicacion,
                "temperatura_requerida": inventario.temperatura_requerida,
                "estado": inventario.estado,
                "condiciones_especiales": inventario.condiciones_especiales,
                "observaciones": inventario.observaciones,
                "fecha_recepcion": inventario.fecha_recepcion.isoformat() if inventario.fecha_recepcion else None,
                "created_at": inventario.created_at.isoformat() if inventario.created_at else None,
                "updated_at": inventario.updated_at.isoformat() if inventario.updated_at else None
            }
            
            producto_id = inventario.producto_id
            
            # Registrar en auditoría ANTES de eliminar (misma transacción)
            audit_log = AuditLog(
                event_type="inventory_operation",
                operation="ELIMINAR",
                inventario_id=inventario.id,
                producto_id=producto_id,
                usuario_id=UUID(usuario_id) if usuario_id else None,
                ip_origen=ip_origen,
                datos_operacion=datos_eliminados,
                cambios=None,
                timestamp=datetime.now(timezone.utc)
            )
            self.db.add(audit_log)
            
            # Eliminar el registro
            self.db.delete(inventario)
            
            # Commit único para ambas operaciones
            self.db.commit()
            self._invalidate_inventario_caches(inventario_id)
            
            await self._notificar_actualizacion_a_productos()
            logger.info(f"Inventario eliminado: {inventario_id} por usuario: {usuario_id}")
            return {"message": f"Registro de inventario {inventario_id} eliminado correctamente"}
            
        except HTTPException:
            raise
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error deleting inventario: {e}")
            raise HTTPException(
                status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
                detail="Error interno al eliminar el registro de inventario."
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

