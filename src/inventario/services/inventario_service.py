from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from fastapi import Depends, HTTPException
from http import HTTPStatus
from datetime import datetime, timezone
import logging
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
                # El esquema asegura que todos estos atributos existen y están tipados
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
            # ... (Manejo de error) ...
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
    

def get_inventario_service(db: Session = Depends(get_db)) -> InventarioService:
    """
    Función de dependencia para obtener una instancia del servicio de inventario.
    """
    return InventarioService(db)

