from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from fastapi import Depends, HTTPException
from http import HTTPStatus
from datetime import datetime, timezone
import logging

from db.database import get_db
from db.vendedor_model import Vendedor
from schemas.vendedor_schema import (
    CrearVendedorSchema,
    ActualizarVendedorSchema,
)

logger = logging.getLogger(__name__)


class VendedorService:
    """
    Servicio de negocio para la gestión de vendedores.

    Responsabilidades:
    - CRUD completo de vendedores
    - Validación de unicidad de email
    - Manejo de errores con HTTPException
    """

    def __init__(self, db: Session = Depends(get_db)):
        """
        Inicializa el servicio con conexión a base de datos.

        Args:
            db: Sesión de SQLAlchemy inyectada por dependencia
        """
        self.db = db

    def crear_vendedor(self, vendedor_data: CrearVendedorSchema) -> Dict[str, Any]:
        """
        Crea un nuevo vendedor en el sistema.

        Pasos:
        1. Verifica que el email no exista
        2. Crea el vendedor en la BD

        Args:
            vendedor_data: Datos del vendedor a crear

        Returns:
            Dict con los datos del vendedor creado

        Raises:
            HTTPException 409: Si el email ya existe
            HTTPException 500: Error interno del servidor
        """
        try:
            # Verificar si el email ya existe
            existing_by_email = self.db.query(Vendedor).filter(
                Vendedor.email == vendedor_data.email
            ).first()

            if existing_by_email:
                raise HTTPException(
                    status_code=HTTPStatus.CONFLICT,
                    detail=f"El email {vendedor_data.email} ya está registrado en el sistema."
                )

            # Crear nuevo vendedor
            nuevo_vendedor = Vendedor(
                nombre=vendedor_data.nombre,
                documento_identidad=vendedor_data.documento_identidad,
                email=vendedor_data.email,
                zona_asignada=vendedor_data.zona_asignada.value,
                plan_venta=vendedor_data.plan_venta,
                meta_venta=vendedor_data.meta_venta
            )

            self.db.add(nuevo_vendedor)
            self.db.commit()
            self.db.refresh(nuevo_vendedor)

            logger.info(f"Vendedor creado exitosamente: {nuevo_vendedor.id}")

            return nuevo_vendedor.to_dict()

        except HTTPException:
            raise
        except IntegrityError as e:
            self.db.rollback()
            logger.error(f"Error de integridad al crear vendedor: {e}")
            raise HTTPException(
                status_code=HTTPStatus.CONFLICT,
                detail="El email ya existe en el sistema."
            )
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error al crear vendedor: {e}")
            raise HTTPException(
                status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
                detail="Error interno al crear el vendedor."
            )

    def obtener_vendedor(self, vendedor_id: str) -> Dict[str, Any]:
        """
        Obtiene un vendedor por su ID.

        Args:
            vendedor_id: UUID del vendedor

        Returns:
            Dict con los datos del vendedor

        Raises:
            HTTPException 404: Vendedor no encontrado
            HTTPException 500: Error interno
        """
        try:
            vendedor = self.db.query(Vendedor).filter(
                Vendedor.id == vendedor_id
            ).first()

            if not vendedor:
                raise HTTPException(
                    status_code=HTTPStatus.NOT_FOUND,
                    detail=f"Vendedor con ID {vendedor_id} no encontrado."
                )

            return vendedor.to_dict()

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error al obtener vendedor {vendedor_id}: {e}")
            raise HTTPException(
                status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
                detail="Error interno al obtener el vendedor."
            )

    def listar_vendedores(
        self,
        skip: int = 0,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Lista todos los vendedores con filtros opcionales.

        Args:
            skip: Número de registros a saltar (paginación)
            limit: Número máximo de registros a retornar

        Returns:
            Lista de vendedores
        """
        try:
            query = self.db.query(Vendedor)

            query = query.order_by(Vendedor.fecha_creacion.desc())

            vendedores = query.offset(skip).limit(limit).all()

            return [vendedor.to_dict() for vendedor in vendedores]

        except Exception as e:
            logger.error(f"Error al listar vendedores: {e}")
            raise HTTPException(
                status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
                detail="Error interno al listar vendedores."
            )

    def actualizar_vendedor(
        self,
        vendedor_id: str,
        vendedor_data: ActualizarVendedorSchema
    ) -> Dict[str, Any]:
        """
        Actualiza un vendedor existente.

        Pasos:
        1. Verifica que el vendedor exista
        2. Si se actualiza el email, verifica que no exista en otro vendedor
        3. Actualiza solo los campos proporcionados

        Args:
            vendedor_id: ID del vendedor a actualizar
            vendedor_data: Datos a actualizar

        Returns:
            Dict con los datos del vendedor actualizado

        Raises:
            HTTPException 404: Vendedor no encontrado
            HTTPException 409: Email ya existe en otro vendedor
        """
        try:
            vendedor = self.db.query(Vendedor).filter(
                Vendedor.id == vendedor_id
            ).first()

            if not vendedor:
                raise HTTPException(
                    status_code=HTTPStatus.NOT_FOUND,
                    detail=f"Vendedor con ID {vendedor_id} no encontrado."
                )

            # Verificar si el nuevo email ya existe en otro vendedor
            if vendedor_data.email and vendedor_data.email != vendedor.email:
                existing_by_email = self.db.query(Vendedor).filter(
                    Vendedor.email == vendedor_data.email,
                    Vendedor.id != vendedor_id
                ).first()

                if existing_by_email:
                    raise HTTPException(
                        status_code=HTTPStatus.CONFLICT,
                        detail=f"El email {vendedor_data.email} ya está registrado en otro vendedor."
                    )

            # Actualizar solo los campos proporcionados
            update_data = vendedor_data.model_dump(exclude_unset=True)

            for field, value in update_data.items():
                if value is not None:
                    # Convertir enums a sus valores
                    if hasattr(value, 'value'):
                        value = value.value
                    setattr(vendedor, field, value)

            vendedor.fecha_actualizacion = datetime.now(timezone.utc)

            self.db.commit()
            self.db.refresh(vendedor)

            logger.info(f"Vendedor actualizado exitosamente: {vendedor_id}")

            return vendedor.to_dict()

        except HTTPException:
            raise
        except IntegrityError as e:
            self.db.rollback()
            logger.error(f"Error de integridad al actualizar vendedor: {e}")
            raise HTTPException(
                status_code=HTTPStatus.CONFLICT,
                detail="El email ya existe en otro vendedor."
            )
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error al actualizar vendedor {vendedor_id}: {e}")
            raise HTTPException(
                status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
                detail="Error interno al actualizar el vendedor."
            )

    def contar_vendedores(self) -> int:
        """
        Cuenta el número total de vendedores con filtros opcionales.

        Returns:
            Número total de vendedores
        """
        try:
            query = self.db.query(Vendedor)

            return query.count()

        except Exception as e:
            logger.error(f"Error al contar vendedores: {e}")
            raise HTTPException(
                status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
                detail="Error interno al contar vendedores."
            )


def get_vendedor_service(db: Session = Depends(get_db)) -> VendedorService:
    """
    Función de dependencia para obtener una instancia del servicio de vendedores.

    Esta función se usa en los routers con Depends() para inyección de dependencias.
    """
    return VendedorService(db)
