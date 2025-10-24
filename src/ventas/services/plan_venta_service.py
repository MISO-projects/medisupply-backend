from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from fastapi import Depends, HTTPException
from http import HTTPStatus
from datetime import datetime, timezone
import logging

from db.database import get_db
from db.plan_venta_model import PlanVenta
from schemas.plan_venta_schema import (
    CrearPlanVentaSchema,
    ActualizarPlanVentaSchema,
)

logger = logging.getLogger(__name__)


class PlanVentaService:
    """
    Servicio de negocio para la gestión de planes de venta.

    Responsabilidades:
    - CRUD completo de planes de venta
    - Validación de rangos de fechas
    - Validación de solapamiento de planes (opcional)
    - Manejo de errores con HTTPException
    """

    def __init__(self, db: Session = Depends(get_db)):
        """
        Inicializa el servicio con conexión a base de datos.

        Args:
            db: Sesión de SQLAlchemy inyectada por dependencia
        """
        self.db = db

    def crear_plan_venta(self, plan_data: CrearPlanVentaSchema) -> Dict[str, Any]:
        """
        Crea un nuevo plan de venta en el sistema.

        Validaciones:
        1. El nombre debe ser único
        2. Las fechas ya vienen validadas por Pydantic (fecha_fin > fecha_inicio)
        3. meta_venta debe ser positiva (validado por Pydantic)

        Args:
            plan_data: Datos del plan de venta a crear

        Returns:
            Dict con los datos del plan creado

        Raises:
            HTTPException 409: Si el nombre ya existe
            HTTPException 500: Error interno del servidor
        """
        try:
            # Verificar si el nombre ya existe
            existing_by_nombre = self.db.query(PlanVenta).filter(
                PlanVenta.nombre == plan_data.nombre
            ).first()

            if existing_by_nombre:
                raise HTTPException(
                    status_code=HTTPStatus.CONFLICT,
                    detail=f"Ya existe un plan de venta con el nombre '{plan_data.nombre}'."
                )

            # Crear nuevo plan de venta
            nuevo_plan = PlanVenta(
                nombre=plan_data.nombre,
                fecha_inicio=plan_data.fecha_inicio,
                fecha_fin=plan_data.fecha_fin,
                descripcion=plan_data.descripcion,
                meta_venta=plan_data.meta_venta,
                zona_asignada=plan_data.zona_asignada.value if plan_data.zona_asignada else None
            )

            self.db.add(nuevo_plan)
            self.db.commit()
            self.db.refresh(nuevo_plan)

            logger.info(f"Plan de venta creado exitosamente: {nuevo_plan.id}")

            return nuevo_plan.to_dict()

        except HTTPException:
            raise
        except IntegrityError as e:
            self.db.rollback()
            logger.error(f"Error de integridad al crear plan de venta: {e}")
            raise HTTPException(
                status_code=HTTPStatus.CONFLICT,
                detail="El nombre del plan de venta ya existe en el sistema."
            )
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error al crear plan de venta: {e}")
            raise HTTPException(
                status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
                detail="Error interno al crear el plan de venta."
            )

    def obtener_plan_venta(self, plan_id: str) -> Dict[str, Any]:
        """
        Obtiene un plan de venta por su ID.

        Args:
            plan_id: UUID del plan de venta

        Returns:
            Dict con los datos del plan

        Raises:
            HTTPException 404: Plan de venta no encontrado
            HTTPException 500: Error interno
        """
        try:
            plan = self.db.query(PlanVenta).filter(
                PlanVenta.id == plan_id
            ).first()

            if not plan:
                raise HTTPException(
                    status_code=HTTPStatus.NOT_FOUND,
                    detail=f"Plan de venta con ID {plan_id} no encontrado."
                )

            return plan.to_dict()

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error al obtener plan de venta {plan_id}: {e}")
            raise HTTPException(
                status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
                detail="Error interno al obtener el plan de venta."
            )

    def listar_planes_venta(
        self,
        skip: int = 0,
        limit: int = 100,
        zona_asignada: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Lista todos los planes de venta con filtros opcionales.

        Args:
            skip: Número de registros a saltar (paginación)
            limit: Número máximo de registros a retornar
            zona_asignada: Filtrar por zona específica (opcional)

        Returns:
            Lista de planes de venta
        """
        try:
            query = self.db.query(PlanVenta)

            # Filtro por zona
            if zona_asignada:
                query = query.filter(PlanVenta.zona_asignada == zona_asignada)

            # Ordenar por fecha de inicio descendente (más recientes primero)
            query = query.order_by(PlanVenta.fecha_inicio.desc())

            planes = query.offset(skip).limit(limit).all()

            return [plan.to_dict() for plan in planes]

        except Exception as e:
            logger.error(f"Error al listar planes de venta: {e}")
            raise HTTPException(
                status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
                detail="Error interno al listar planes de venta."
            )

    def actualizar_plan_venta(
        self,
        plan_id: str,
        plan_data: ActualizarPlanVentaSchema
    ) -> Dict[str, Any]:
        """
        Actualiza un plan de venta existente.

        Pasos:
        1. Verifica que el plan exista
        2. Si se actualiza el nombre, verifica que no exista en otro plan
        3. Si se actualizan fechas, valida la coherencia
        4. Actualiza solo los campos proporcionados

        Args:
            plan_id: ID del plan de venta a actualizar
            plan_data: Datos a actualizar

        Returns:
            Dict con los datos del plan actualizado

        Raises:
            HTTPException 404: Plan no encontrado
            HTTPException 409: Nombre ya existe en otro plan
            HTTPException 400: Fechas inválidas
        """
        try:
            plan = self.db.query(PlanVenta).filter(
                PlanVenta.id == plan_id
            ).first()

            if not plan:
                raise HTTPException(
                    status_code=HTTPStatus.NOT_FOUND,
                    detail=f"Plan de venta con ID {plan_id} no encontrado."
                )

            # Verificar si el nuevo nombre ya existe en otro plan
            if plan_data.nombre and plan_data.nombre != plan.nombre:
                existing_by_nombre = self.db.query(PlanVenta).filter(
                    PlanVenta.nombre == plan_data.nombre,
                    PlanVenta.id != plan_id
                ).first()

                if existing_by_nombre:
                    raise HTTPException(
                        status_code=HTTPStatus.CONFLICT,
                        detail=f"Ya existe otro plan de venta con el nombre '{plan_data.nombre}'."
                    )

            # Actualizar solo los campos proporcionados
            update_data = plan_data.model_dump(exclude_unset=True)

            # Validar fechas si se actualizan ambas o alguna
            fecha_inicio_nueva = update_data.get('fecha_inicio', plan.fecha_inicio)
            fecha_fin_nueva = update_data.get('fecha_fin', plan.fecha_fin)

            if fecha_fin_nueva <= fecha_inicio_nueva:
                raise HTTPException(
                    status_code=HTTPStatus.BAD_REQUEST,
                    detail="La fecha_fin debe ser posterior a la fecha_inicio."
                )

            for field, value in update_data.items():
                if value is not None:
                    # Convertir enums a sus valores
                    if hasattr(value, 'value'):
                        value = value.value
                    setattr(plan, field, value)

            plan.fecha_actualizacion = datetime.now(timezone.utc)

            self.db.commit()
            self.db.refresh(plan)

            logger.info(f"Plan de venta actualizado exitosamente: {plan_id}")

            return plan.to_dict()

        except HTTPException:
            raise
        except IntegrityError as e:
            self.db.rollback()
            logger.error(f"Error de integridad al actualizar plan de venta: {e}")
            raise HTTPException(
                status_code=HTTPStatus.CONFLICT,
                detail="El nombre del plan de venta ya existe en otro plan."
            )
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error al actualizar plan de venta {plan_id}: {e}")
            raise HTTPException(
                status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
                detail="Error interno al actualizar el plan de venta."
            )

    def eliminar_plan_venta(self, plan_id: str) -> Dict[str, str]:
        """
        Elimina un plan de venta del sistema.

        Args:
            plan_id: ID del plan de venta a eliminar

        Returns:
            Dict con mensaje de confirmación

        Raises:
            HTTPException 404: Plan no encontrado
            HTTPException 500: Error interno
        """
        try:
            plan = self.db.query(PlanVenta).filter(
                PlanVenta.id == plan_id
            ).first()

            if not plan:
                raise HTTPException(
                    status_code=HTTPStatus.NOT_FOUND,
                    detail=f"Plan de venta con ID {plan_id} no encontrado."
                )

            self.db.delete(plan)
            self.db.commit()

            logger.info(f"Plan de venta eliminado exitosamente: {plan_id}")

            return {"message": f"Plan de venta {plan_id} eliminado exitosamente"}

        except HTTPException:
            raise
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error al eliminar plan de venta {plan_id}: {e}")
            raise HTTPException(
                status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
                detail="Error interno al eliminar el plan de venta."
            )

    def contar_planes_venta(
        self,
        zona_asignada: Optional[str] = None
    ) -> int:
        """
        Cuenta el número total de planes de venta con filtros opcionales.

        Args:
            zona_asignada: Filtrar por zona específica

        Returns:
            Número total de planes de venta
        """
        try:
            query = self.db.query(PlanVenta)

            # Aplicar los mismos filtros que listar_planes_venta
            if zona_asignada:
                query = query.filter(PlanVenta.zona_asignada == zona_asignada)

            return query.count()

        except Exception as e:
            logger.error(f"Error al contar planes de venta: {e}")
            raise HTTPException(
                status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
                detail="Error interno al contar planes de venta."
            )


def get_plan_venta_service(db: Session = Depends(get_db)) -> PlanVentaService:
    """
    Función de dependencia para obtener una instancia del servicio de planes de venta.

    Esta función se usa en los routers con Depends() para inyección de dependencias.
    """
    return PlanVentaService(db)
