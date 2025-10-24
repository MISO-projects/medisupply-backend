from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from fastapi import HTTPException, status, Depends
from typing import List
import logging
import math

from db.database import get_db
from models.ruta_model import Conductor
from schemas.conductor_schema import (
    ConductorCreateRequest,
    ConductorUpdateRequest,
    ConductorResponse,
    ConductoresListResponse
)

logger = logging.getLogger(__name__)


class ConductorService:
    def __init__(self, db: Session):
        self.db = db

    def crear_conductor(self, conductor_data: ConductorCreateRequest) -> ConductorResponse:
        """Crea un nuevo conductor"""
        try:
            # Verificar si el documento ya existe
            conductor_existente = self.db.query(Conductor).filter(
                Conductor.documento == conductor_data.documento
            ).first()
            
            if conductor_existente:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Ya existe un conductor con el documento {conductor_data.documento}"
                )
            
            nuevo_conductor = Conductor(
                nombre=conductor_data.nombre,
                apellido=conductor_data.apellido,
                documento=conductor_data.documento,
                telefono=conductor_data.telefono,
                email=conductor_data.email,
                licencia_conducir=conductor_data.licencia_conducir,
                activo=conductor_data.activo
            )
            
            self.db.add(nuevo_conductor)
            self.db.commit()
            self.db.refresh(nuevo_conductor)
            
            logger.info(f"Conductor creado con ID: {nuevo_conductor.id}")
            
            return ConductorResponse(**nuevo_conductor.to_dict())
            
        except HTTPException:
            raise
        except IntegrityError as e:
            self.db.rollback()
            logger.error(f"Error de integridad al crear conductor: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Error de integridad de datos al crear el conductor"
            )
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error inesperado al crear conductor: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error al crear el conductor: {str(e)}"
            )

    def obtener_conductor(self, conductor_id: int) -> ConductorResponse:
        """Obtiene un conductor por ID"""
        try:
            conductor = self.db.query(Conductor).filter(Conductor.id == conductor_id).first()
            
            if not conductor:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Conductor con ID {conductor_id} no encontrado"
                )
            
            return ConductorResponse(**conductor.to_dict())
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error al obtener conductor {conductor_id}: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error al obtener el conductor: {str(e)}"
            )

    def listar_conductores(self, page: int = 1, page_size: int = 20, activo: bool = None) -> ConductoresListResponse:
        """Lista todos los conductores con paginación"""
        try:
            skip = (page - 1) * page_size
            
            query = self.db.query(Conductor)
            
            # Filtrar por estado activo si se especifica
            if activo is not None:
                query = query.filter(Conductor.activo == activo)
            
            total = query.count()
            total_pages = math.ceil(total / page_size) if total > 0 else 0
            
            conductores = query.offset(skip).limit(page_size).all()
            
            conductores_response = [
                ConductorResponse(**conductor.to_dict())
                for conductor in conductores
            ]
            
            return ConductoresListResponse(
                total=total,
                page=page,
                page_size=page_size,
                total_pages=total_pages,
                conductores=conductores_response
            )
            
        except Exception as e:
            logger.error(f"Error al listar conductores: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error al listar los conductores: {str(e)}"
            )

    def actualizar_conductor(self, conductor_id: int, conductor_data: ConductorUpdateRequest) -> ConductorResponse:
        """Actualiza un conductor existente"""
        try:
            conductor = self.db.query(Conductor).filter(Conductor.id == conductor_id).first()
            
            if not conductor:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Conductor con ID {conductor_id} no encontrado"
                )
            
            # Actualizar solo los campos proporcionados
            update_data = conductor_data.model_dump(exclude_unset=True)
            
            # Verificar documento único si se está actualizando
            if 'documento' in update_data:
                conductor_existente = self.db.query(Conductor).filter(
                    Conductor.documento == update_data['documento'],
                    Conductor.id != conductor_id
                ).first()
                
                if conductor_existente:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Ya existe otro conductor con el documento {update_data['documento']}"
                    )
            
            for key, value in update_data.items():
                setattr(conductor, key, value)
            
            self.db.commit()
            self.db.refresh(conductor)
            
            logger.info(f"Conductor {conductor_id} actualizado exitosamente")
            
            return ConductorResponse(**conductor.to_dict())
            
        except HTTPException:
            raise
        except IntegrityError as e:
            self.db.rollback()
            logger.error(f"Error de integridad al actualizar conductor: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Error de integridad de datos al actualizar el conductor"
            )
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error al actualizar conductor {conductor_id}: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error al actualizar el conductor: {str(e)}"
            )

    def eliminar_conductor(self, conductor_id: int) -> dict:
        """Elimina (desactiva) un conductor"""
        try:
            conductor = self.db.query(Conductor).filter(Conductor.id == conductor_id).first()
            
            if not conductor:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Conductor con ID {conductor_id} no encontrado"
                )
            
            # En lugar de eliminar, desactivar
            conductor.activo = False
            self.db.commit()
            
            logger.info(f"Conductor {conductor_id} desactivado exitosamente")
            
            return {"mensaje": f"Conductor {conductor_id} desactivado exitosamente"}
            
        except HTTPException:
            raise
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error al eliminar conductor {conductor_id}: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error al eliminar el conductor: {str(e)}"
            )


def get_conductor_service(db: Session = Depends(get_db)) -> ConductorService:
    """Función de dependencia para inyectar el servicio de conductores"""
    return ConductorService(db=db)

