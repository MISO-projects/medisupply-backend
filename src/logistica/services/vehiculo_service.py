from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from fastapi import HTTPException, status, Depends
from typing import List
import logging
import math

from db.database import get_db
from models.ruta_model import Vehiculo
from schemas.vehiculo_schema import (
    VehiculoCreateRequest,
    VehiculoUpdateRequest,
    VehiculoResponse,
    VehiculosListResponse
)

logger = logging.getLogger(__name__)


class VehiculoService:
    def __init__(self, db: Session):
        self.db = db

    def crear_vehiculo(self, vehiculo_data: VehiculoCreateRequest) -> VehiculoResponse:
        """Crea un nuevo vehículo"""
        try:
            # Verificar si la placa ya existe
            vehiculo_existente = self.db.query(Vehiculo).filter(
                Vehiculo.placa == vehiculo_data.placa
            ).first()
            
            if vehiculo_existente:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Ya existe un vehículo con la placa {vehiculo_data.placa}"
                )
            
            nuevo_vehiculo = Vehiculo(
                placa=vehiculo_data.placa,
                marca=vehiculo_data.marca,
                modelo=vehiculo_data.modelo,
                año=vehiculo_data.año,
                tipo=vehiculo_data.tipo,
                capacidad_kg=vehiculo_data.capacidad_kg,
                activo=vehiculo_data.activo
            )
            
            self.db.add(nuevo_vehiculo)
            self.db.commit()
            self.db.refresh(nuevo_vehiculo)
            
            logger.info(f"Vehículo creado con ID: {nuevo_vehiculo.id}")
            
            return VehiculoResponse(**nuevo_vehiculo.to_dict())
            
        except HTTPException:
            raise
        except IntegrityError as e:
            self.db.rollback()
            logger.error(f"Error de integridad al crear vehículo: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Error de integridad de datos al crear el vehículo"
            )
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error inesperado al crear vehículo: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error al crear el vehículo: {str(e)}"
            )

    def obtener_vehiculo(self, vehiculo_id: int) -> VehiculoResponse:
        """Obtiene un vehículo por ID"""
        try:
            vehiculo = self.db.query(Vehiculo).filter(Vehiculo.id == vehiculo_id).first()
            
            if not vehiculo:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Vehículo con ID {vehiculo_id} no encontrado"
                )
            
            return VehiculoResponse(**vehiculo.to_dict())
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error al obtener vehículo {vehiculo_id}: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error al obtener el vehículo: {str(e)}"
            )

    def listar_vehiculos(self, page: int = 1, page_size: int = 20, activo: bool = None) -> VehiculosListResponse:
        """Lista todos los vehículos con paginación"""
        try:
            skip = (page - 1) * page_size
            
            query = self.db.query(Vehiculo)
            
            # Filtrar por estado activo si se especifica
            if activo is not None:
                query = query.filter(Vehiculo.activo == activo)
            
            total = query.count()
            total_pages = math.ceil(total / page_size) if total > 0 else 0
            
            vehiculos = query.offset(skip).limit(page_size).all()
            
            vehiculos_response = [
                VehiculoResponse(**vehiculo.to_dict())
                for vehiculo in vehiculos
            ]
            
            return VehiculosListResponse(
                total=total,
                page=page,
                page_size=page_size,
                total_pages=total_pages,
                vehiculos=vehiculos_response
            )
            
        except Exception as e:
            logger.error(f"Error al listar vehículos: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error al listar los vehículos: {str(e)}"
            )

    def actualizar_vehiculo(self, vehiculo_id: int, vehiculo_data: VehiculoUpdateRequest) -> VehiculoResponse:
        """Actualiza un vehículo existente"""
        try:
            vehiculo = self.db.query(Vehiculo).filter(Vehiculo.id == vehiculo_id).first()
            
            if not vehiculo:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Vehículo con ID {vehiculo_id} no encontrado"
                )
            
            # Actualizar solo los campos proporcionados
            update_data = vehiculo_data.model_dump(exclude_unset=True)
            
            # Verificar placa única si se está actualizando
            if 'placa' in update_data:
                vehiculo_existente = self.db.query(Vehiculo).filter(
                    Vehiculo.placa == update_data['placa'],
                    Vehiculo.id != vehiculo_id
                ).first()
                
                if vehiculo_existente:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Ya existe otro vehículo con la placa {update_data['placa']}"
                    )
            
            for key, value in update_data.items():
                setattr(vehiculo, key, value)
            
            self.db.commit()
            self.db.refresh(vehiculo)
            
            logger.info(f"Vehículo {vehiculo_id} actualizado exitosamente")
            
            return VehiculoResponse(**vehiculo.to_dict())
            
        except HTTPException:
            raise
        except IntegrityError as e:
            self.db.rollback()
            logger.error(f"Error de integridad al actualizar vehículo: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Error de integridad de datos al actualizar el vehículo"
            )
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error al actualizar vehículo {vehiculo_id}: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error al actualizar el vehículo: {str(e)}"
            )

    def eliminar_vehiculo(self, vehiculo_id: int) -> dict:
        """Elimina (desactiva) un vehículo"""
        try:
            vehiculo = self.db.query(Vehiculo).filter(Vehiculo.id == vehiculo_id).first()
            
            if not vehiculo:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Vehículo con ID {vehiculo_id} no encontrado"
                )
            
            # En lugar de eliminar, desactivar
            vehiculo.activo = False
            self.db.commit()
            
            logger.info(f"Vehículo {vehiculo_id} desactivado exitosamente")
            
            return {"mensaje": f"Vehículo {vehiculo_id} desactivado exitosamente"}
            
        except HTTPException:
            raise
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error al eliminar vehículo {vehiculo_id}: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error al eliminar el vehículo: {str(e)}"
            )


def get_vehiculo_service(db: Session = Depends(get_db)) -> VehiculoService:
    """Función de dependencia para inyectar el servicio de vehículos"""
    return VehiculoService(db=db)

