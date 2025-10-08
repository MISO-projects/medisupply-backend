from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from fastapi import Depends, HTTPException
from http import HTTPStatus
from datetime import datetime, timezone
import logging

from db.database import get_db
from db.proveedor_model import Proveedor
from schemas.proveedor_schema import (
    CrearProveedorSchema,
    ActualizarProveedorSchema,
)

logger = logging.getLogger(__name__)


class ProveedorService:
    def __init__(self, db: Session = Depends(get_db)):
        self.db = db

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
            proveedor = self.db.query(Proveedor).filter(
                Proveedor.id == proveedor_id
            ).first()
            
            if not proveedor:
                raise HTTPException(
                    status_code=HTTPStatus.NOT_FOUND,
                    detail=f"Proveedor con ID {proveedor_id} no encontrado."
                )
            
            return proveedor.to_dict()
            
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
            query = self.db.query(Proveedor)
            
            if pais:
                query = query.filter(Proveedor.pais == pais)
            
            if tipo_proveedor:
                query = query.filter(Proveedor.tipo_proveedor == tipo_proveedor)
            
            query = query.order_by(Proveedor.fecha_creacion.desc())
            
            proveedores = query.offset(skip).limit(limit).all()
            
            return [proveedor.to_dict() for proveedor in proveedores]
            
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
            update_data = proveedor_data.model_dump(exclude_unset=True)
            
            for field, value in update_data.items():
                if value is not None:
                    # Convertir enums a sus valores
                    if hasattr(value, 'value'):
                        value = value.value
                    setattr(proveedor, field, value)
            
            proveedor.fecha_actualizacion = datetime.now(timezone.utc)
            
            self.db.commit()
            self.db.refresh(proveedor)
            
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
            query = self.db.query(Proveedor)
            
            if pais:
                query = query.filter(Proveedor.pais == pais)
            
            if tipo_proveedor:
                query = query.filter(Proveedor.tipo_proveedor == tipo_proveedor)
            
            return query.count()
            
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

