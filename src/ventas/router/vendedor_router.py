from fastapi import APIRouter, Depends, Query, status
from typing import Optional
import logging

from services.vendedor_service import VendedorService, get_vendedor_service
from schemas.vendedor_schema import (
    CrearVendedorSchema,
    ActualizarVendedorSchema,
    ZonaAsignadaEnum
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

vendedor_router = APIRouter()


@vendedor_router.post(
    "/",
    response_model=dict,
    status_code=status.HTTP_201_CREATED,
    summary="Crear nuevo vendedor",
    description="Crea un nuevo vendedor en el sistema con validación de email único",
    responses={
        201: {
            "description": "Vendedor creado exitosamente",
            "content": {
                "application/json": {
                    "example": {
                        "message": "Creación exitosa",
                        "data": {
                            "id": "550e8400-e29b-41d4-a716-446655440000",
                            "nombre": "Juan Pérez",
                            "email": "juan.perez@medisupply.com",
                            "zona_asignada": "Perú"
                        }
                    }
                }
            }
        },
        409: {"description": "Email ya existe"},
        422: {"description": "Error de validación en los datos"}
    }
)
async def crear_vendedor(
    vendedor: CrearVendedorSchema,
    vendedor_service: VendedorService = Depends(get_vendedor_service)
):
    """
    Crea un nuevo vendedor con los siguientes datos:

    - **nombre**: Nombre completo del vendedor (obligatorio)
    - **documento_identidad**: Documento de identidad (opcional)
    - **email**: Email válido y único (obligatorio)
    - **zona_asignada**: Zona/país asignado (obligatorio)
    - **plan_venta**: ID del plan de venta (opcional)
    - **meta_venta**: Meta de ventas en monto monetario (opcional)
    """
    data = vendedor_service.crear_vendedor(vendedor)
    return {
        "message": "Creación exitosa",
        "data": data
    }


@vendedor_router.get(
    "/",
    response_model=dict,
    summary="Listar vendedores",
    description="Obtiene listado de vendedores con paginación",
    responses={
        200: {
            "description": "Lista de vendedores obtenida exitosamente",
            "content": {
                "application/json": {
                    "example": {
                        "data": [
                            {
                                "id": "550e8400-e29b-41d4-a716-446655440000",
                                "nombre": "Juan Pérez",
                                "email": "juan.perez@medisupply.com",
                                "zona_asignada": "Perú",
                                "meta_venta": "50000.00"
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
async def listar_vendedores(
    page: int = Query(1, ge=1, description="Número de página"),
    page_size: int = Query(20, ge=1, le=100, description="Tamaño de página (máximo 100)"),
    vendedor_service: VendedorService = Depends(get_vendedor_service)
):
    """
    Lista todos los vendedores con opciones de:

    - **Paginación**: Con page (número de página) y page_size (tamaño)
    - **Ordenamiento**: Por fecha de creación (más recientes primero)
    """
    skip = (page - 1) * page_size

    vendedores = vendedor_service.listar_vendedores(
        skip=skip,
        limit=page_size
    )

    total = vendedor_service.contar_vendedores()

    return {
        "data": vendedores,
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": (total + page_size - 1) // page_size if total > 0 else 0
    }


@vendedor_router.get(
    "/{vendedor_id}",
    response_model=dict,
    summary="Obtener vendedor por ID",
    description="Obtiene los detalles completos de un vendedor específico",
    responses={
        200: {"description": "Vendedor encontrado"},
        404: {"description": "Vendedor no encontrado"}
    }
)
async def obtener_vendedor(
    vendedor_id: str,
    vendedor_service: VendedorService = Depends(get_vendedor_service)
):
    """
    Obtiene toda la información de un vendedor específico por su ID.
    """
    data = vendedor_service.obtener_vendedor(vendedor_id)
    return {
        "data": data
    }


@vendedor_router.put(
    "/{vendedor_id}",
    response_model=dict,
    summary="Actualizar vendedor",
    description="Actualiza los datos de un vendedor existente",
    responses={
        200: {"description": "Vendedor actualizado exitosamente"},
        404: {"description": "Vendedor no encontrado"},
        409: {"description": "Email ya existe en otro vendedor"},
        422: {"description": "Error de validación en los datos"}
    }
)
async def actualizar_vendedor(
    vendedor_id: str,
    vendedor: ActualizarVendedorSchema,
    vendedor_service: VendedorService = Depends(get_vendedor_service)
):
    """
    Actualiza un vendedor existente.

    - Solo se actualizan los campos que se envíen en el request
    - El documento de identidad no se puede cambiar
    - El email debe ser único si se actualiza
    """
    data = vendedor_service.actualizar_vendedor(vendedor_id, vendedor)
    return {
        "message": "Vendedor actualizado exitosamente",
        "data": data
    }
