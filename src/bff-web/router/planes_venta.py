from fastapi import APIRouter, Depends, Query, status
from typing import Optional
import logging

from services.planes_venta_service import PlanesVentaService, get_planes_venta_service
from schemas.plan_venta_schema import (
    CrearPlanVentaSchema,
    ActualizarPlanVentaSchema,
)
from schemas.vendedor_schema import ZonaAsignadaEnum

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

planes_venta_router = APIRouter()


@planes_venta_router.post(
    "",
    response_model=dict,
    status_code=status.HTTP_201_CREATED,
    summary="Crear nuevo plan de venta",
    description="Crea un nuevo plan de venta en el sistema con validación de nombre único",
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
                            "meta_venta": "100000.00",
                            "zona_asignada": "Perú"
                        }
                    }
                }
            }
        },
        409: {"description": "Nombre del plan ya existe"},
        422: {"description": "Error de validación en los datos"}
    }
)
async def crear_plan_venta(
    plan: CrearPlanVentaSchema,
    planes_service: PlanesVentaService = Depends(get_planes_venta_service)
):
    """
    Crea un nuevo plan de venta con los siguientes datos:

    - **nombre**: Nombre del plan (obligatorio, único)
    - **fecha_inicio**: Fecha de inicio del plan (obligatorio)
    - **fecha_fin**: Fecha de fin del plan (obligatorio, debe ser posterior a fecha_inicio)
    - **meta_venta**: Meta de ventas en monto monetario (obligatorio, mayor a 0)
    - **descripcion**: Descripción del plan (opcional)
    - **zona_asignada**: Zona/país asignado (opcional)
    """
    data = await planes_service.crear_plan_venta(plan.model_dump())
    return data


@planes_venta_router.get(
    "",
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
    nombre: Optional[str] = Query(None, description="Filtrar por nombre (búsqueda parcial)"),
    zona_asignada: Optional[str] = Query(None, description="Filtrar por zona asignada"),
    planes_service: PlanesVentaService = Depends(get_planes_venta_service)
):
    """
    Lista todos los planes de venta con opciones de:

    - **Paginación**: Con page (número de página) y page_size (tamaño)
    - **Filtros**: Por nombre y zona_asignada
    - **Ordenamiento**: Por fecha de creación (más recientes primero)
    """
    data = await planes_service.listar_planes_venta(
        page=page,
        page_size=page_size,
        nombre=nombre,
        zona_asignada=zona_asignada
    )

    return data


@planes_venta_router.get(
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
    planes_service: PlanesVentaService = Depends(get_planes_venta_service)
):
    """
    Obtiene toda la información de un plan de venta específico por su ID.
    """
    data = await planes_service.obtener_plan_venta(plan_id)
    return data


@planes_venta_router.put(
    "/{plan_id}",
    response_model=dict,
    summary="Actualizar plan de venta",
    description="Actualiza los datos de un plan de venta existente",
    responses={
        200: {"description": "Plan de venta actualizado exitosamente"},
        404: {"description": "Plan de venta no encontrado"},
        409: {"description": "Nombre ya existe en otro plan"},
        422: {"description": "Error de validación en los datos"}
    }
)
async def actualizar_plan_venta(
    plan_id: str,
    plan: ActualizarPlanVentaSchema,
    planes_service: PlanesVentaService = Depends(get_planes_venta_service)
):
    """
    Actualiza un plan de venta existente.

    - Solo se actualizan los campos que se envíen en el request
    - El nombre debe ser único si se actualiza
    - Si se actualiza fecha_fin, debe ser posterior a fecha_inicio
    """
    data = await planes_service.actualizar_plan_venta(
        plan_id,
        plan.model_dump(exclude_unset=True)
    )
    return data


@planes_venta_router.delete(
    "/{plan_id}",
    response_model=dict,
    summary="Eliminar plan de venta",
    description="Elimina un plan de venta del sistema",
    responses={
        200: {"description": "Plan de venta eliminado exitosamente"},
        404: {"description": "Plan de venta no encontrado"}
    }
)
async def eliminar_plan_venta(
    plan_id: str,
    planes_service: PlanesVentaService = Depends(get_planes_venta_service)
):
    """
    Elimina un plan de venta específico por su ID.

    NOTA: No se puede eliminar un plan que tenga vendedores asociados.
    """
    data = await planes_service.eliminar_plan_venta(plan_id)
    return data
