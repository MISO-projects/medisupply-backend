from fastapi import APIRouter, Depends, Query, status
from typing import Optional
import logging

from services.plan_venta_service import PlanVentaService, get_plan_venta_service
from schemas.plan_venta_schema import (
    CrearPlanVentaSchema,
    ActualizarPlanVentaSchema,
)
from schemas.vendedor_schema import ZonaAsignadaEnum

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

plan_venta_router = APIRouter()


@plan_venta_router.post(
    "/",
    response_model=dict,
    status_code=status.HTTP_201_CREATED,
    summary="Crear nuevo plan de venta",
    description="Crea un nuevo plan de venta en el sistema con validación de fechas, meta y nombre único",
    responses={
        201: {
            "description": "Plan de venta creado exitosamente",
            "content": {
                "application/json": {
                    "example": {
                        "message": "Creación exitosa",
                        "data": {
                            "id": "550e8400-e29b-41d4-a716-446655440000",
                            "nombre": "Plan Q1 2024 - Perú",
                            "fecha_inicio": "2024-01-01T00:00:00",
                            "fecha_fin": "2024-03-31T23:59:59",
                            "descripcion": "Plan trimestral para Perú",
                            "meta_venta": "100000.00",
                            "zona_asignada": "Perú"
                        }
                    }
                }
            }
        },
        400: {"description": "Datos inválidos (ej: fecha_fin antes de fecha_inicio)"},
        409: {"description": "El nombre del plan ya existe"},
        422: {"description": "Error de validación en los datos"}
    }
)
async def crear_plan_venta(
    plan: CrearPlanVentaSchema,
    plan_service: PlanVentaService = Depends(get_plan_venta_service)
):
    """
    Crea un nuevo plan de venta con los siguientes datos:

    - **nombre**: Nombre descriptivo del plan (obligatorio, único)
    - **fecha_inicio**: Fecha de inicio del plan (obligatorio)
    - **fecha_fin**: Fecha de finalización (obligatorio, debe ser posterior a fecha_inicio)
    - **descripcion**: Descripción detallada del plan (opcional)
    - **meta_venta**: Meta de ventas en monto monetario (obligatorio, debe ser > 0)
    - **zona_asignada**: Zona geográfica asignada (opcional)
    """
    data = plan_service.crear_plan_venta(plan)
    return {
        "message": "Creación exitosa",
        "data": data
    }


@plan_venta_router.get(
    "/",
    response_model=dict,
    summary="Listar planes de venta",
    description="Obtiene listado de planes de venta con paginación y filtros opcionales",
    responses={
        200: {
            "description": "Lista de planes de venta obtenida exitosamente",
            "content": {
                "application/json": {
                    "example": {
                        "data": [
                            {
                                "id": "550e8400-e29b-41d4-a716-446655440000",
                                "nombre": "Plan Q1 2024 - Perú",
                                "fecha_inicio": "2024-01-01T00:00:00",
                                "fecha_fin": "2024-03-31T23:59:59",
                                "meta_venta": "100000.00",
                                "zona_asignada": "Perú"
                            }
                        ],
                        "total": 1,
                        "page": 1,
                        "page_size": 20,
                        "total_pages": 1
                    }
                }
            }
        }
    }
)
async def listar_planes_venta(
    page: int = Query(1, ge=1, description="Número de página"),
    page_size: int = Query(20, ge=1, le=100, description="Tamaño de página (máximo 100)"),
    zona_asignada: Optional[ZonaAsignadaEnum] = Query(None, description="Filtrar por zona específica"),
    plan_service: PlanVentaService = Depends(get_plan_venta_service)
):
    """
    Lista todos los planes de venta con opciones de:

    - **Paginación**: Con page (número de página) y page_size (tamaño)
    - **Filtrado por zona**: Opcional, filtra por zona geográfica específica
    - **Ordenamiento**: Por fecha de inicio (más recientes primero)
    """
    skip = (page - 1) * page_size

    planes = plan_service.listar_planes_venta(
        skip=skip,
        limit=page_size,
        zona_asignada=zona_asignada.value if zona_asignada else None
    )

    total = plan_service.contar_planes_venta(
        zona_asignada=zona_asignada.value if zona_asignada else None
    )

    return {
        "data": planes,
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": (total + page_size - 1) // page_size if total > 0 else 0
    }


@plan_venta_router.get(
    "/{plan_id}",
    response_model=dict,
    summary="Obtener plan de venta por ID",
    description="Obtiene los detalles completos de un plan de venta específico",
    responses={
        200: {"description": "Plan de venta encontrado"},
        404: {"description": "Plan de venta no encontrado"}
    }
)
async def obtener_plan_venta(
    plan_id: str,
    plan_service: PlanVentaService = Depends(get_plan_venta_service)
):
    """
    Obtiene toda la información de un plan de venta específico por su ID.
    """
    data = plan_service.obtener_plan_venta(plan_id)
    return {
        "data": data
    }


@plan_venta_router.put(
    "/{plan_id}",
    response_model=dict,
    summary="Actualizar plan de venta",
    description="Actualiza los datos de un plan de venta existente",
    responses={
        200: {"description": "Plan de venta actualizado exitosamente"},
        404: {"description": "Plan de venta no encontrado"},
        400: {"description": "Fechas inválidas"},
        409: {"description": "El nombre ya existe en otro plan"},
        422: {"description": "Error de validación en los datos"}
    }
)
async def actualizar_plan_venta(
    plan_id: str,
    plan: ActualizarPlanVentaSchema,
    plan_service: PlanVentaService = Depends(get_plan_venta_service)
):
    """
    Actualiza un plan de venta existente.

    - Solo se actualizan los campos que se envíen en el request
    - El nombre debe ser único si se actualiza
    - Si se actualizan fechas, se valida que fecha_fin > fecha_inicio
    - La meta_venta debe ser positiva si se actualiza
    """
    data = plan_service.actualizar_plan_venta(plan_id, plan)
    return {
        "message": "Plan de venta actualizado exitosamente",
        "data": data
    }


@plan_venta_router.delete(
    "/{plan_id}",
    response_model=dict,
    status_code=status.HTTP_200_OK,
    summary="Eliminar plan de venta",
    description="Elimina un plan de venta del sistema",
    responses={
        200: {"description": "Plan de venta eliminado exitosamente"},
        404: {"description": "Plan de venta no encontrado"}
    }
)
async def eliminar_plan_venta(
    plan_id: str,
    plan_service: PlanVentaService = Depends(get_plan_venta_service)
):
    """
    Elimina un plan de venta del sistema por su ID.

    **Advertencia**: Esta acción es permanente y no se puede deshacer.
    """
    result = plan_service.eliminar_plan_venta(plan_id)
    return result
