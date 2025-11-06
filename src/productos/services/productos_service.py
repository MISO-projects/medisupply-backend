# src/productos/services/productos_service.py

from sqlalchemy.orm import Session
from sqlalchemy import and_
from sqlalchemy.dialects.postgresql import insert
from typing import List, Optional, Union
import uuid as uuid_module
from models.producto import Producto
from schemas.producto_schema import (
    ProductoCreate, 
    ProductoUpdate, 
    ProductoResponse,
    MobileProducto,
    BulkUploadError,
    BulkUploadResponse,
    MissingFieldError,
    BulkUploadValidationError
)
from fastapi import HTTPException, UploadFile
import logging
import httpx
import os
from http import HTTPStatus
from typing import Dict, Any
import json
import pandas as pd
from decimal import Decimal, InvalidOperation
from uuid import UUID
import io

from db.redis_client import get_redis_client

logger = logging.getLogger(__name__)


class ProductosService:
    CACHE_TTL_PRODUCTO = 3600
    CACHE_TTL_LIST = 300

    def __init__(self, db: Session):
        self.db = db
        self.redis_client = get_redis_client()
        self.proveedores_service_url = os.getenv(
            "PROVEEDORES_SERVICE_URL", "http://proveedores-service:3000"
        )
        self.inventario_service_url = os.getenv(
            "INVENTARIO_SERVICE_URL", "http://inventario-service:3000"
        )
    
    def _get_cache(self, key: str) -> Optional[Any]:
        """Get data from cache"""
        try:
            if self.redis_client is None: return None
            cached_data = self.redis_client.get(key)
            if cached_data: return json.loads(cached_data)
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

    def _invalidate_producto_caches(self, producto_id: Optional[str] = None) -> None:
        """Invalidate all producto-related caches"""
        try:
            if producto_id:
                self._delete_cache(f"producto:{producto_id}")
            # Invalidate list caches
            self._delete_cache("productos:list:*")
            self._delete_cache("productos:mobile:list:*")
        except Exception as e:
            logger.warning(f"Error invalidating caches: {e}")
    
    def invalidar_cache_de_listas(self) -> None:
        """
        Invalida todos los cachés de listas (móvil y web).
        Este método está diseñado para ser llamado por un webhook
        (ej. desde el servicio de inventario) cuando el stock cambia.
        """
        try:
            logger.info("Iniciando invalidación de caché de listas (webhook)...")
            self._delete_cache("productos:list:*")
            self._delete_cache("productos:mobile:list:*")
            logger.info("Cachés de listas de productos invalidados (webhook).")
        except Exception as e:
            logger.warning(f"Error durante la invalidación de caché por webhook: {e}")
    
    async def _get_stock_para_productos(self, producto_ids: List[str]) -> Dict[str, int]:
        if not producto_ids: return {}
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(
                    f"{self.inventario_service_url}/api/inventario/stock/batch",
                    json={"producto_ids": producto_ids}
                )
                if response.status_code == 200:
                    return response.json().get("stock_data", {}) 
                else:
                    logger.error(f"Error al obtener stock: {response.status_code} - {response.text}")
                    return {}
        except httpx.RequestError as e:
            logger.error(f"Error de conexión al servicio de inventario: {e}")
            return {}

    async def get_productos_disponibles_mobile(
        self,
        nombre: Optional[str] = None,
        categoria: Optional[str] = None,      
        disponibilidad: Optional[bool] = None,
        skip: int = 0,
        limit: int = 20,
    ) -> tuple[List[MobileProducto], int]:
        """
        Obtiene la lista de productos disponibles, enriquecida con stock
        del servicio de inventario para el móvil, con filtros.
        """
        try:
            cache_key = f"productos:mobile:list:{nombre or 'all'}:{categoria or 'all'}:{disponibilidad}:{skip}:{limit}"
            cached_data = self._get_cache(cache_key)
            
            if cached_data is not None:
                logger.debug(f"Cache hit for productos mobile list")
                productos_list = [MobileProducto(**p) for p in cached_data.get('productos', [])]
                return productos_list, cached_data.get('total', 0)
            
            logger.debug(f"Cache miss for productos mobile list")
            
            # Construir query base
            query = self.db.query(Producto)

            # Aplicar filtros
            filters = [Producto.disponible == True]

            if nombre:
                filters.append(Producto.nombre.ilike(f"%{nombre}%"))
            
            if categoria:
                filters.append(Producto.categoria == categoria)

            query = query.filter(and_(*filters))

            total_en_catalogo = query.count()
            logger.debug(f"Total productos en catálogo (sin filtro stock): {total_en_catalogo}")

            productos_db = query.order_by(Producto.nombre).offset(skip).limit(limit).all()
            
            if not productos_db:
                return [], 0
            producto_ids = [str(p.id) for p in productos_db]
            stock_map = await self._get_stock_para_productos(producto_ids)
            productos_finales = []
            for producto in productos_db:
                stock_actual = stock_map.get(str(producto.id), 0)
                if disponibilidad is None:
                    pass
                elif disponibilidad is True and stock_actual == 0:
                    continue
                elif disponibilidad is False and stock_actual > 0:
                    continue

                producto_dict = producto.to_dict() 
                producto_dict['stock_disponible'] = stock_actual
                
                productos_finales.append(MobileProducto.model_validate(producto_dict))
            cache_data = {
                'productos': [p.model_dump(mode='json', by_alias=True) for p in productos_finales],
                'total': total_en_catalogo 
            }
            self._set_cache(cache_key, cache_data, self.CACHE_TTL_LIST)

            logger.info(f"Retornando {len(productos_finales)} productos para el móvil")
            return productos_finales, total_en_catalogo

        except Exception as e:
            logger.error(f"Error al obtener productos disponibles: {str(e)}")
            raise HTTPException(
                status_code=500, detail="Error al obtener productos disponibles"
            )
        
    async def get_productos_creados_web(
        self,
        categoria: Optional[str] = None,      
        nombre: Optional[str] = None, 
        skip: int = 0,
        limit: int = 20,
    ) -> tuple[List[ProductoResponse], int]: 
        """
        Obtiene la lista de productos creados para la WEB (SIN STOCK).
        """
        try:
            query = self.db.query(Producto)
            filters = [] 

            if nombre:
                filters.append(Producto.nombre.ilike(f"%{nombre}%"))
            if categoria:
                filters.append(Producto.categoria == categoria)
            
            if filters:
                query = query.filter(and_(*filters))

            total_en_catalogo = query.count()
            logger.debug(f"Total productos en catálogo: {total_en_catalogo}")

            productos_db = query.order_by(Producto.nombre).offset(skip).limit(limit).all()
            
            if not productos_db:
                return [], 0

            productos_finales = [ProductoResponse.model_validate(p) for p in productos_db]

            logger.info(f"Retornando {len(productos_finales)} productos creados")
            return productos_finales, total_en_catalogo

        except Exception as e:
            logger.error(f"Error al obtener productos creados: {str(e)}")
            raise HTTPException(
                status_code=500, detail="Error al obtener productos creados"
            )

    def _get_producto_model_by_id(self, producto_id: str) -> Producto:
        """
        Obtiene el modelo SQLAlchemy de un producto por su ID (para uso interno).
        No usa cache porque se necesita el objeto de la sesión para operaciones de escritura.
        """
        try:
            producto = (
                self.db.query(Producto).filter(Producto.id == producto_id).first()
            )
            if not producto:
                raise HTTPException(
                    status_code=404,
                    detail=f"Producto con ID {producto_id} no encontrado",
                )
            return producto
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error al obtener producto {producto_id}: {str(e)}")
            raise HTTPException(status_code=500, detail="Error al obtener producto")

    def get_producto_by_id(self, producto_id: str) -> ProductoResponse:
        """Obtiene un producto por su ID (con cache)"""
        try:
            cache_key = f"producto:{producto_id}"
            cached_data = self._get_cache(cache_key)
            
            if cached_data is not None:
                logger.debug(f"Cache hit for producto {producto_id}")
                return ProductoResponse(**cached_data)
            
            logger.debug(f"Cache miss for producto {producto_id}")
            producto = self._get_producto_model_by_id(producto_id)
            
            producto_dict = producto.to_dict()
            self._set_cache(cache_key, producto_dict, self.CACHE_TTL_PRODUCTO)
            
            return ProductoResponse.model_validate(producto)
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error al obtener producto {producto_id}: {str(e)}")
            raise HTTPException(status_code=500, detail="Error al obtener producto")

    async def _verificar_proveedor_activo(self, proveedor_id: str) -> Dict[str, Any]:
        """
        Verifica que el proveedor existe y está activo.

        Args:
            proveedor_id: ID del proveedor

        Returns:
            Dict con los datos del proveedor

        Raises:
            HTTPException: Si el proveedor no existe o no está disponible
        """
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(
                    f"{self.proveedores_service_url}/proveedores/{proveedor_id}"
                )

                if response.status_code == 404:
                    raise HTTPException(
                        status_code=HTTPStatus.BAD_REQUEST,
                        detail=f"El proveedor con ID {proveedor_id} no existe en el sistema.",
                    )
                elif response.status_code != 200:
                    raise HTTPException(
                        status_code=HTTPStatus.BAD_REQUEST,
                        detail="No se pudo verificar el proveedor. Intente nuevamente.",
                    )

                data = response.json()
                return data.get("data", {})

        except httpx.RequestError as e:
            logger.error(f"Error al verificar proveedor {proveedor_id}: {e}")
            return {"id": proveedor_id, "nombre": "Proveedor (no verificado)"}

    async def crear_producto(self, producto_data: ProductoCreate) -> Dict[str, Any]:
        """Crea un nuevo producto"""
        try:
            proveedor_info = await self._verificar_proveedor_activo(
                producto_data.proveedor_id
            )
            if producto_data.sku:
                existing = self.db.query(Producto).filter(Producto.sku == producto_data.sku).first()
                if existing:
                    raise HTTPException(status_code=400, detail=f"Ya existe un producto con el SKU {producto_data.sku}")

            nuevo_producto = Producto(
                **producto_data.model_dump(),
                proveedor_nombre=proveedor_info.get("nombre", "Proveedor (no verificado)")
            )
            
            self.db.add(nuevo_producto)
            self.db.commit()
            self.db.refresh(nuevo_producto)

            self._invalidate_producto_caches()
            logger.info(f"Producto creado: {nuevo_producto.id} - {nuevo_producto.nombre}")
            
            return nuevo_producto.to_dict()

        except HTTPException:
            raise
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error al crear producto: {str(e)}")
            raise HTTPException(status_code=500, detail="Error al crear producto")
    def actualizar_producto(
        self, producto_id: str, producto_data: ProductoUpdate
    ) -> Producto:
        """Actualiza un producto existente"""
        try:
            producto = self._get_producto_model_by_id(producto_id)

            # Actualizar solo los campos proporcionados
            update_data = producto_data.model_dump(exclude_unset=True)

            # Verificar SKU único si se está actualizando
            if "sku" in update_data and update_data["sku"]:
                existing = (
                    self.db.query(Producto)
                    .filter(
                        Producto.sku == update_data["sku"], Producto.id != producto_id
                    )
                    .first()
                )
                if existing:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Ya existe otro producto con el SKU {update_data['sku']}",
                    )

            for field, value in update_data.items():
                setattr(producto, field, value)

            self.db.commit()
            self.db.refresh(producto)

            self._invalidate_producto_caches(producto_id)

            logger.info(f"Producto actualizado: {producto.id}")
            return producto

        except HTTPException:
            raise
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error al actualizar producto {producto_id}: {str(e)}")
            raise HTTPException(status_code=500, detail="Error al actualizar producto")

    def eliminar_producto(self, producto_id: str) -> bool:
        """Elimina un producto (soft delete marcándolo como no disponible)"""
        try:
            producto = self._get_producto_model_by_id(producto_id)
            producto.disponible = False
            self.db.commit()

            self._invalidate_producto_caches(producto_id)

            logger.info(f"Producto marcado como no disponible: {producto_id}")
            return True

        except HTTPException:
            raise
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error al eliminar producto {producto_id}: {str(e)}")
            raise HTTPException(status_code=500, detail="Error al eliminar producto")

    def get_detalles_por_ids(self, producto_ids: List[str]) -> Dict[str, Dict[str, str]]:
        """
        Obtiene detalles clave (nombre y SKU) para una lista de IDs de productos.
        """
        try:
            unique_ids = list(set(producto_ids))
            productos_db = self.db.query(
                Producto.id, 
                Producto.nombre, 
                Producto.sku
            ).filter(
                Producto.id.in_(unique_ids)
            ).all()

            # Convertimos la lista en un diccionario para búsqueda rápida
            # Ej: {"uuid-1": {"nombre": "Guantes", "sku": "SKU-123"}, ...}
            detalles_map = {
                str(p.id): {"nombre": p.nombre, "sku": p.sku}
                for p in productos_db
            }
            
            logger.info(f"Se obtuvieron detalles para {len(detalles_map)} productos.")
            return detalles_map

        except Exception as e:
            logger.error(f"Error al obtener detalles de productos por IDs: {str(e)}")
            return {}

    def get_productos_by_ids(self, ids: List[str]) -> List[ProductoResponse]:
        """Obtiene productos por una lista de IDs."""
        try:
            if not ids:
                return []

            productos = (
                self.db.query(Producto)
                .filter(Producto.id.in_(ids))
                .all()
            )

            return [ProductoResponse.model_validate(p) for p in productos]
        except Exception as e:
            logger.error(f"Error al obtener productos por IDs: {str(e)}")
            raise HTTPException(status_code=500, detail="Error al obtener productos por IDs")

    async def bulk_upload_productos(self, file: UploadFile) -> BulkUploadResponse:
        """
        Procesa un archivo Excel con productos y los crea en lote.
        
        Columnas esperadas en el Excel:
        - nombre (requerido)
        - descripcion (opcional)
        - categoria (requerido)
        - imagen_url (opcional)
        - precio_unitario (requerido)
        - disponible (opcional, default: true)
        - unidad_medida (opcional, default: UNIDAD)
        - sku (opcional, se genera automático si no se provee)
        - tipo_almacenamiento (opcional, default: AMBIENTE)
        - observaciones (opcional)
        - proveedor_id (requerido, UUID)
        """
        errors = []
        created_products = []
        updated_products = []
        duplicate_rows = []
        total_rows = 0
        
        try:
            contents = await file.read()
            df = pd.read_excel(io.BytesIO(contents), engine='openpyxl')
            total_rows = len(df)
            
            logger.info(f"Procesando archivo Excel con {total_rows} filas")
            
            if total_rows == 0:
                raise HTTPException(
                    status_code=400,
                    detail="El archivo Excel está vacío"
                )
            
            required_columns = ['nombre', 'categoria', 'precio_unitario', 'proveedor_id']
            missing_columns = [col for col in required_columns if col not in df.columns]
            
            if missing_columns:
                raise HTTPException(
                    status_code=400,
                    detail=f"Columnas requeridas faltantes: {', '.join(missing_columns)}"
                )
            
            df['disponible'] = df['disponible'].fillna(True)
            df['unidad_medida'] = df['unidad_medida'].fillna('UNIDAD')
            df['tipo_almacenamiento'] = df['tipo_almacenamiento'].fillna('AMBIENTE')
            
            missing_data_errors = []
            for idx, row in df.iterrows():
                row_number = idx + 2
                missing_fields = []
                
                if pd.isna(row['nombre']) or str(row['nombre']).strip() == '':
                    missing_fields.append('nombre')
                if pd.isna(row['categoria']) or str(row['categoria']).strip() == '':
                    missing_fields.append('categoria')
                if pd.isna(row['precio_unitario']):
                    missing_fields.append('precio_unitario')
                if pd.isna(row['proveedor_id']) or str(row['proveedor_id']).strip() == '':
                    missing_fields.append('proveedor_id')
                
                if missing_fields:
                    missing_data_errors.append(
                        MissingFieldError(
                            row=row_number,
                            missing_fields=missing_fields
                        )
                    )
            
            if missing_data_errors:
                validation_error = BulkUploadValidationError(
                    message="Campos requeridos faltantes en algunas filas",
                    missing_data=missing_data_errors
                )
                raise HTTPException(
                    status_code=400,
                    detail=validation_error.model_dump()
                )
            
            proveedor_ids = df['proveedor_id'].unique().tolist()
            proveedores_cache = await self._verificar_proveedores_batch(proveedor_ids)
            
            seen_skus = set()
            productos_to_upsert = []
            
            for idx, row in df.iterrows():
                row_number = idx + 2
                
                try:
                    proveedor_id_str = str(row['proveedor_id']).strip()
                    
                    try:
                        proveedor_uuid = UUID(proveedor_id_str)
                    except (ValueError, AttributeError):
                        errors.append(BulkUploadError(
                            row=row_number,
                            error=f"proveedor_id inválido: {proveedor_id_str}",
                            data={"proveedor_id": proveedor_id_str}
                        ))
                        continue
                    
                    if proveedor_id_str not in proveedores_cache:
                        errors.append(BulkUploadError(
                            row=row_number,
                            error=f"Proveedor no encontrado: {proveedor_id_str}",
                            data={"proveedor_id": proveedor_id_str}
                        ))
                        continue
                    
                    try:
                        precio = Decimal(str(row['precio_unitario']))
                        if precio <= 0:
                            raise ValueError("El precio debe ser mayor a 0")
                    except (InvalidOperation, ValueError) as e:
                        errors.append(BulkUploadError(
                            row=row_number,
                            error=f"precio_unitario inválido: {str(e)}",
                            data={"precio_unitario": str(row['precio_unitario'])}
                        ))
                        continue
                    
                    sku_value = row['sku'] if pd.notna(row['sku']) and str(row['sku']).strip() else None
                    
                    if not sku_value:
                        sku_value = Producto._generate_sku()
                        while sku_value in seen_skus:
                            sku_value = Producto._generate_sku()
                    
                    if sku_value in seen_skus:
                        duplicate_rows.append(row_number)
                        logger.debug(f"Fila {row_number} con SKU duplicado en el archivo, ignorando")
                        continue
                    
                    seen_skus.add(sku_value)
                    
                    disponible_value = True
                    if pd.notna(row['disponible']):
                        disponible_str = str(row['disponible']).lower().strip()
                        disponible_value = disponible_str in ['true', '1', 'si', 'yes', 'sí']
                    
                    nombre_producto = str(row['nombre']).strip()
                    
                    producto_dict = {
                        'id': str(uuid_module.uuid4()),
                        'nombre': nombre_producto,
                        'descripcion': str(row['descripcion']).strip() if pd.notna(row['descripcion']) else None,
                        'categoria': str(row['categoria']).strip(),
                        'imagen_url': str(row['imagen_url']).strip() if pd.notna(row['imagen_url']) else None,
                        'precio_unitario': precio,
                        'disponible': disponible_value,
                        'unidad_medida': str(row['unidad_medida']).strip() if pd.notna(row['unidad_medida']) else 'UNIDAD',
                        'sku': sku_value,
                        'tipo_almacenamiento': str(row['tipo_almacenamiento']).strip() if pd.notna(row['tipo_almacenamiento']) else 'AMBIENTE',
                        'observaciones': str(row['observaciones']).strip() if pd.notna(row['observaciones']) else None,
                        'proveedor_id': proveedor_uuid,
                        'proveedor_nombre': proveedores_cache[proveedor_id_str]
                    }
                    
                    productos_to_upsert.append(producto_dict)
                    
                except Exception as e:
                    logger.error(f"Error procesando fila {row_number}: {str(e)}")
                    errors.append(BulkUploadError(
                        row=row_number,
                        error=str(e),
                        data=row.to_dict() if hasattr(row, 'to_dict') else None
                    ))
                    continue
            
            if productos_to_upsert:
                existing_skus_in_db = {p.sku for p in self.db.query(Producto.sku).filter(
                    Producto.sku.in_([p['sku'] for p in productos_to_upsert])
                ).all()}
                
                stmt = insert(Producto).values(productos_to_upsert)
                
                update_dict = {
                    'nombre': stmt.excluded.nombre,
                    'descripcion': stmt.excluded.descripcion,
                    'categoria': stmt.excluded.categoria,
                    'imagen_url': stmt.excluded.imagen_url,
                    'precio_unitario': stmt.excluded.precio_unitario,
                    'disponible': stmt.excluded.disponible,
                    'unidad_medida': stmt.excluded.unidad_medida,
                    'tipo_almacenamiento': stmt.excluded.tipo_almacenamiento,
                    'observaciones': stmt.excluded.observaciones,
                    'proveedor_id': stmt.excluded.proveedor_id,
                    'proveedor_nombre': stmt.excluded.proveedor_nombre,
                }
                
                stmt = stmt.on_conflict_do_update(
                    index_elements=['sku'],
                    set_=update_dict
                )
                
                self.db.execute(stmt)
                self.db.flush()
                
                for producto in productos_to_upsert:
                    if producto['sku'] in existing_skus_in_db:
                        updated_products.append(producto['id'])
                    else:
                        created_products.append(producto['id'])
            
            if created_products or updated_products:
                self.db.commit()
                self._invalidate_producto_caches()
                logger.info(f"Bulk upload completado: {len(created_products)} creados, {len(updated_products)} actualizados, {len(errors)} errores, {len(duplicate_rows)} duplicados")
            else:
                self.db.rollback()
                logger.warning("No se creó ni actualizó ningún producto en el bulk upload")
            
            return BulkUploadResponse(
                total_rows=total_rows,
                successful=len(created_products) + len(updated_products),
                failed=len(errors),
                created=len(created_products),
                updated=len(updated_products),
                skipped_duplicates=len(duplicate_rows),
                duplicate_rows=duplicate_rows,
                errors=errors,
                created_products=created_products,
                updated_products=updated_products
            )
            
        except HTTPException:
            raise
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error crítico en bulk upload: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail=f"Error al procesar archivo: {str(e)}"
            )

    async def _verificar_proveedores_batch(self, proveedor_ids: List) -> Dict[str, str]:
        """
        Verifica múltiples proveedores en una sola llamada y retorna un cache
        con {proveedor_id: proveedor_nombre}
        """
        proveedores_cache = {}
        
        for proveedor_id in proveedor_ids:
            if pd.isna(proveedor_id):
                continue
                
            try:
                proveedor_id_str = str(proveedor_id).strip()
                proveedor_info = await self._verificar_proveedor_activo(proveedor_id_str)
                proveedores_cache[proveedor_id_str] = proveedor_info.get("nombre", "Proveedor")
            except HTTPException:
                pass
            except Exception as e:
                logger.warning(f"Error verificando proveedor {proveedor_id}: {e}")
                
        return proveedores_cache
