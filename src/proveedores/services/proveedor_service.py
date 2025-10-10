from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from fastapi import Depends, HTTPException
from http import HTTPStatus
from datetime import datetime, timezone
import logging
import json

from db.database import get_db
from db.proveedor_model import Proveedor
from db.redis_client import get_redis_client
from schemas.proveedor_schema import (
    CrearProveedorSchema,
    ActualizarProveedorSchema,
)

logger = logging.getLogger(__name__)


class ProveedorService:
    CACHE_TTL_PROVEEDOR = 3600  # 1 hour for individual provider
    CACHE_TTL_LIST = 300  # 5 minutes for lists
    CACHE_TTL_COUNT = 300  # 5 minutes for counts

    def __init__(self, db: Session = Depends(get_db)):
        self.db = db
        self.redis_client = get_redis_client()

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
            self.redis_client.setex(key, ttl, json.dumps(value))
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

    def _invalidate_proveedor_caches(self, proveedor_id: Optional[str] = None) -> None:
        """Invalidate all proveedor-related caches"""
        try:
            if proveedor_id:
                self._delete_cache(f"proveedor:{proveedor_id}")
            # Invalidate list and count caches
            self._delete_cache("proveedores:list:*")
            self._delete_cache("proveedores:count:*")
        except Exception as e:
            logger.warning(f"Error invalidating caches: {e}")

    def crear_proveedor(self, proveedor_data: CrearProveedorSchema) -> Dict[str, Any]:
        """
        Crea un nuevo proveedor en el sistema.
        
        Args:
            proveedor_data: Datos del proveedor a crear
            
        Returns:
            Dict con los datos del proveedor creado
            
        Raises:
            HTTPException: Si el id_tributario o email ya existen
        """
        try:
            # Verificar si el id_tributario ya existe
            existing_by_id_tributario = self.db.query(Proveedor).filter(
                Proveedor.id_tributario == proveedor_data.id_tributario
            ).first()
            
            if existing_by_id_tributario:
                raise HTTPException(
                    status_code=HTTPStatus.CONFLICT,
                    detail=f"El ID tributario {proveedor_data.id_tributario} ya está registrado en el sistema."
                )
            
            # Verificar si el email ya existe
            existing_by_email = self.db.query(Proveedor).filter(
                Proveedor.email == proveedor_data.email
            ).first()
            
            if existing_by_email:
                raise HTTPException(
                    status_code=HTTPStatus.CONFLICT,
                    detail=f"El email {proveedor_data.email} ya está registrado en el sistema."
                )
            
            nuevo_proveedor = Proveedor(
                nombre=proveedor_data.nombre,
                id_tributario=proveedor_data.id_tributario,
                tipo_proveedor=proveedor_data.tipo_proveedor.value,
                email=proveedor_data.email,
                pais=proveedor_data.pais.value,
                contacto=proveedor_data.contacto,
                condiciones_entrega=proveedor_data.condiciones_entrega
            )
            
            self.db.add(nuevo_proveedor)
            self.db.commit()
            self.db.refresh(nuevo_proveedor)
            
            self._invalidate_proveedor_caches()
            
            logger.info(f"Proveedor creado exitosamente: {nuevo_proveedor.id}")
            
            return nuevo_proveedor.to_dict()
            
        except HTTPException:
            raise
        except IntegrityError as e:
            self.db.rollback()
            logger.error(f"Error de integridad al crear proveedor: {e}")
            raise HTTPException(
                status_code=HTTPStatus.CONFLICT,
                detail="El ID tributario o email ya existe en el sistema."
            )
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error al crear proveedor: {e}")
            raise HTTPException(
                status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
                detail="Error interno al crear el proveedor."
            )

    def obtener_proveedor(self, proveedor_id: str) -> Dict[str, Any]:
        """
        Obtiene un proveedor por su ID.
        
        Args:
            proveedor_id: ID del proveedor
            
        Returns:
            Dict con los datos del proveedor
            
        Raises:
            HTTPException: Si el proveedor no existe
        """
        try:
            cache_key = f"proveedor:{proveedor_id}"
            cached_data = self._get_cache(cache_key)
            
            if cached_data is not None:
                logger.debug(f"Cache hit for proveedor {proveedor_id}")
                return cached_data
            
            logger.debug(f"Cache miss for proveedor {proveedor_id}")
            proveedor = self.db.query(Proveedor).filter(
                Proveedor.id == proveedor_id
            ).first()
            
            if not proveedor:
                raise HTTPException(
                    status_code=HTTPStatus.NOT_FOUND,
                    detail=f"Proveedor con ID {proveedor_id} no encontrado."
                )
            
            proveedor_dict = proveedor.to_dict()
            
            self._set_cache(cache_key, proveedor_dict, self.CACHE_TTL_PROVEEDOR)
            
            return proveedor_dict
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error al obtener proveedor {proveedor_id}: {e}")
            raise HTTPException(
                status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
                detail="Error interno al obtener el proveedor."
            )

    def listar_proveedores(
        self,
        pais: Optional[str] = None,
        tipo_proveedor: Optional[str] = None,
        skip: int = 0,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Lista todos los proveedores con filtros opcionales.
        
        Args:
            pais: Filtrar por país (opcional)
            tipo_proveedor: Filtrar por tipo de proveedor (opcional)
            skip: Número de registros a saltar (paginación)
            limit: Número máximo de registros a retornar
            
        Returns:
            Lista de proveedores
        """
        try:
            cache_key = f"proveedores:list:{pais or 'all'}:{tipo_proveedor or 'all'}:{skip}:{limit}"
            cached_data = self._get_cache(cache_key)
            
            if cached_data is not None:
                logger.debug(f"Cache hit for proveedores list")
                return cached_data
            
            logger.debug(f"Cache miss for proveedores list")
            query = self.db.query(Proveedor)
            
            if pais:
                query = query.filter(Proveedor.pais == pais)
            
            if tipo_proveedor:
                query = query.filter(Proveedor.tipo_proveedor == tipo_proveedor)
            
            query = query.order_by(Proveedor.fecha_creacion.desc())
            
            proveedores = query.offset(skip).limit(limit).all()
            
            proveedores_list = [proveedor.to_dict() for proveedor in proveedores]
            
            self._set_cache(cache_key, proveedores_list, self.CACHE_TTL_LIST)
            
            return proveedores_list
            
        except Exception as e:
            logger.error(f"Error al listar proveedores: {e}")
            raise HTTPException(
                status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
                detail="Error interno al listar proveedores."
            )

    def actualizar_proveedor(
        self,
        proveedor_id: str,
        proveedor_data: ActualizarProveedorSchema
    ) -> Dict[str, Any]:
        """
        Actualiza un proveedor existente.
        
        Args:
            proveedor_id: ID del proveedor a actualizar
            proveedor_data: Datos a actualizar
            
        Returns:
            Dict con los datos del proveedor actualizado
            
        Raises:
            HTTPException: Si el proveedor no existe o hay conflicto con datos únicos
        """
        try:
            proveedor = self.db.query(Proveedor).filter(
                Proveedor.id == proveedor_id
            ).first()
            
            if not proveedor:
                raise HTTPException(
                    status_code=HTTPStatus.NOT_FOUND,
                    detail=f"Proveedor con ID {proveedor_id} no encontrado."
                )
            
            # Verificar si el nuevo email ya existe en otro proveedor
            if proveedor_data.email and proveedor_data.email != proveedor.email:
                existing_by_email = self.db.query(Proveedor).filter(
                    Proveedor.email == proveedor_data.email,
                    Proveedor.id != proveedor_id
                ).first()
                
                if existing_by_email:
                    raise HTTPException(
                        status_code=HTTPStatus.CONFLICT,
                        detail=f"El email {proveedor_data.email} ya está registrado en otro proveedor."
                    )
            
            # Actualizar solo los campos que se proporcionaron
            update_data = proveedor_data.model_dump(exclude_unset=True, exclude_none=True)
            
            for field, value in update_data.items():
                if value is not None:
                    # Convertir enums a sus valores
                    if hasattr(value, 'value'):
                        value = value.value
                    setattr(proveedor, field, value)
            
            proveedor.fecha_actualizacion = datetime.now(timezone.utc)
            
            self.db.commit()
            self.db.refresh(proveedor)
            
            self._invalidate_proveedor_caches(proveedor_id)
            
            logger.info(f"Proveedor actualizado exitosamente: {proveedor_id}")
            
            return proveedor.to_dict()
            
        except HTTPException:
            raise
        except IntegrityError as e:
            self.db.rollback()
            logger.error(f"Error de integridad al actualizar proveedor: {e}")
            raise HTTPException(
                status_code=HTTPStatus.CONFLICT,
                detail="El email ya existe en otro proveedor."
            )
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error al actualizar proveedor {proveedor_id}: {e}")
            raise HTTPException(
                status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
                detail="Error interno al actualizar el proveedor."
            )

    def eliminar_proveedor(self, proveedor_id: str) -> Dict[str, str]:
        """
        Elimina un proveedor del sistema.
        
        Args:
            proveedor_id: ID del proveedor a eliminar
            
        Returns:
            Dict con mensaje de confirmación
            
        Raises:
            HTTPException: Si el proveedor no existe
        """
        try:
            proveedor = self.db.query(Proveedor).filter(
                Proveedor.id == proveedor_id
            ).first()
            
            if not proveedor:
                raise HTTPException(
                    status_code=HTTPStatus.NOT_FOUND,
                    detail=f"Proveedor con ID {proveedor_id} no encontrado."
                )
            
            self.db.delete(proveedor)
            self.db.commit()
            
            self._invalidate_proveedor_caches(proveedor_id)
            
            logger.info(f"Proveedor eliminado exitosamente: {proveedor_id}")
            
            return {"message": "Proveedor eliminado exitosamente"}
            
        except HTTPException:
            raise
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error al eliminar proveedor {proveedor_id}: {e}")
            raise HTTPException(
                status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
                detail="Error interno al eliminar el proveedor."
            )

    def contar_proveedores(
        self,
        pais: Optional[str] = None,
        tipo_proveedor: Optional[str] = None
    ) -> int:
        """
        Cuenta el número total de proveedores con filtros opcionales.
        
        Args:
            pais: Filtrar por país (opcional)
            tipo_proveedor: Filtrar por tipo de proveedor (opcional)
            
        Returns:
            Número total de proveedores
        """
        try:
            cache_key = f"proveedores:count:{pais or 'all'}:{tipo_proveedor or 'all'}"
            cached_data = self._get_cache(cache_key)
            
            if cached_data is not None:
                logger.debug(f"Cache hit for proveedores count")
                return cached_data
            
            logger.debug(f"Cache miss for proveedores count")
            query = self.db.query(Proveedor)
            
            if pais:
                query = query.filter(Proveedor.pais == pais)
            
            if tipo_proveedor:
                query = query.filter(Proveedor.tipo_proveedor == tipo_proveedor)
            
            count = query.count()
            
            self._set_cache(cache_key, count, self.CACHE_TTL_COUNT)
            
            return count
            
        except Exception as e:
            logger.error(f"Error al contar proveedores: {e}")
            raise HTTPException(
                status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
                detail="Error interno al contar proveedores."
            )



def get_proveedor_service(db: Session = Depends(get_db)) -> ProveedorService:
    """
    Función de dependencia para obtener una instancia del servicio de proveedores.
    """
    return ProveedorService(db)

