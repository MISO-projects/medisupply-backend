from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from fastapi import Depends, HTTPException
from http import HTTPStatus
from datetime import datetime, timezone
import logging
import httpx
import os
import json

from db.database import get_db
from db.inventario_model import Inventario
from schemas.inventario_schema import CrearRegistroInventarioSchema
from db.redis_client import get_redis_client

logger = logging.getLogger(__name__)


class InventarioService:
    CACHE_TTL_PROVEEDOR = 3600  # 1 hour for individual provider
    CACHE_TTL_LIST = 300  # 5 minutes for lists
    CACHE_TTL_COUNT = 300  # 5 minutes for counts

    def __init__(self, db: Session = Depends(get_db)):
        self.db = db
        self.redis_client = get_redis_client()
        self.productos_service_url = os.getenv(
            "PRODUCTOS_SERVICE_URL", "http://productos-service:3000"
        )

    
    # def _get_cache(self, key: str) -> Optional[Any]:
    #     """Get data from cache"""
    #     try:
    #         if self.redis_client is None:
    #             return None
    #         cached_data = self.redis_client.get(key)
    #         if cached_data:
    #             return json.loads(cached_data)
    #         return None
    #     except Exception as e:
    #         logger.warning(f"Error getting cache for key {key}: {e}")
    #         return None

    # def _set_cache(self, key: str, value: Any, ttl: int) -> None:
    #     """Set data in cache"""
    #     try:
    #         if self.redis_client is None:
    #             return
    #         self.redis_client.setex(key, ttl, json.dumps(value))
    #     except Exception as e:
    #         logger.warning(f"Error setting cache for key {key}: {e}")

    # def _delete_cache(self, pattern: str) -> None:
    #     """Delete cache keys matching pattern"""
    #     try:
    #         if self.redis_client is None:
    #             return
    #         keys = self.redis_client.keys(pattern)
    #         if keys:
    #             self.redis_client.delete(*keys)
    #     except Exception as e:
    #         logger.warning(f"Error deleting cache for pattern {pattern}: {e}")

    # def _invalidate_inventario_caches(self, inventario_id: Optional[str] = None) -> None:
    #     """Invalidate all inventario-related caches"""
    #     try:
    #         if inventario_id:
    #             self._delete_cache(f"inventario:{inventario_id}")
    #         # Invalidate list and count caches
    #         self._delete_cache("inventarioes:list:*")
    #         self._delete_cache("inventarioes:count:*")
    #     except Exception as e:
    #         logger.warning(f"Error invalidating caches: {e}")

    async def _get_detalles_productos(self, producto_ids: List[str]) -> Dict[str, Any]:
        """Obtiene detalles (nombre, SKU) para una lista de IDs de productos."""
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


    def crear_registro_inventario(self, inventario_data: CrearRegistroInventarioSchema) -> Dict[str, Any]:
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

    async def listar_registros_paginados(self, skip: int, limit: int) -> tuple[List[Dict[str, Any]], int]:
        """
        Obtiene una lista paginada de todos los registros de inventario,
        enriquecida con nombre y SKU del servicio de productos.
        """
        try:
            query = self.db.query(Inventario)
            total = query.count()
            
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
                items_enriquecidos.append(registro_dict)
            return items_enriquecidos, total

        except Exception as e:
            logger.error(f"Error al listar registros de inventario paginados: {e}")
            raise HTTPException(
                status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
                detail="Error interno al listar los registros de inventario."
            )

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
    

def get_inventario_service(db: Session = Depends(get_db)) -> InventarioService:
    """
    Función de dependencia para obtener una instancia del servicio de inventario.
    """
    return InventarioService(db)

