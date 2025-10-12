from fastapi import APIRouter, Depends, Query, status
from typing import Optional
import logging

from services.proveedores_service import ProveedoresService, get_proveedores_service
from schemas.proveedor_schema import (
    CrearProveedorSchema,
    ActualizarProveedorSchema,
    PaisEnum,
    TipoProveedorEnum
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

proveedor_router = APIRouter()
@proveedor_router.get("/health")
def health_check(proveedores_service: ProveedoresService = Depends(get_proveedores_service)):
    return proveedores_service.health_check()

@proveedor_router.post(
    "/",
    response_model=dict,
    status_code=status.HTTP_201_CREATED,
    summary="Crear nuevo proveedor",
    description="Crea un nuevo proveedor en el sistema con validaciones de ID tributario y email únicos",
    responses={
        201: {
            "description": "Proveedor creado exitosamente",
            "content": {
                "application/json": {
                    "example": {
                        "message": "Creación exitosa",
                        "data": {
                            "id": "550e8400-e29b-41d4-a716-446655440000",
                            "nombre": "Farmacéutica Nacional S.A.",
                            "id_tributario": "20123456789",
                            "email": "contacto@farmaceutica.com"
                        }
                    }
                }
            }
        },
        409: {"description": "ID tributario o email ya existe"},
        422: {"description": "Error de validación en los datos"}
    }
)
async def crear_proveedor(
    proveedor: CrearProveedorSchema,
    proveedores_service: ProveedoresService = Depends(get_proveedores_service)
):
    """
    Crea un nuevo proveedor con los siguientes datos:
    
    - **nombre**: Nombre del proveedor (máximo 255 caracteres, obligatorio)
    - **id_tributario**: RUC/NIT/RFC según país (único, obligatorio)
    - **tipo_proveedor**: Tipo de proveedor (obligatorio)
    - **email**: Email válido (único, obligatorio)
    - **pais**: País de operación (obligatorio)
    - **contacto**: Información de contacto (opcional, máximo 255 caracteres)
    - **condiciones_entrega**: Condiciones de entrega (opcional, máximo 500 caracteres)
    """
    data = await proveedores_service.crear_proveedor(proveedor.model_dump())
    return data


@proveedor_router.get(
    "/",
    response_model=dict,
    summary="Listar proveedores",
    description="Obtiene listado de proveedores con filtros opcionales y paginación",
    responses={
        200: {
            "description": "Lista de proveedores obtenida exitosamente",
            "content": {
                "application/json": {
                    "example": {
                        "data": [
                            {
                                "id": "550e8400-e29b-41d4-a716-446655440000",
                                "nombre": "Farmacéutica Nacional S.A.",
                                "id_tributario": "20123456789",
                                "tipo_proveedor": "Fabricante",
                                "email": "contacto@farmaceutica.com",
                                "pais": "Perú"
                            }
                        ],
                        "total": 1,
                        "page": 1,
                        "page_size": 20
                    }
                }
            }
        }
    }
)
async def listar_proveedores(
    pais: Optional[PaisEnum] = Query(None, description="Filtrar por país"),
    tipo_proveedor: Optional[TipoProveedorEnum] = Query(None, description="Filtrar por tipo de proveedor"),
    page: int = Query(1, ge=1, description="Número de página"),
    page_size: int = Query(20, ge=1, le=100, description="Tamaño de página (máximo 100)"),
    proveedores_service: ProveedoresService = Depends(get_proveedores_service)
):
    """
    Lista todos los proveedores con opciones de:
    
    - **Filtros**: Por país y tipo de proveedor
    - **Paginación**: Con page (número de página) y page_size (tamaño)
    - **Ordenamiento**: Por fecha de creación (más recientes primero)
    """
    pais_value = pais.value if pais else None
    tipo_value = tipo_proveedor.value if tipo_proveedor else None
    
    data = await proveedores_service.listar_proveedores(
        pais=pais_value,
        tipo_proveedor=tipo_value,
        page=page,
        page_size=page_size
    )
    
    return data


@proveedor_router.get(
    "/{proveedor_id}",
    response_model=dict,
    summary="Obtener proveedor por ID",
    description="Obtiene los detalles completos de un proveedor específico",
    responses={
        200: {"description": "Proveedor encontrado"},
        404: {"description": "Proveedor no encontrado"}
    }
)
async def obtener_proveedor(
    proveedor_id: str,
    proveedores_service: ProveedoresService = Depends(get_proveedores_service)
):
    """
    Obtiene toda la información de un proveedor específico por su ID.
    """
    data = await proveedores_service.obtener_proveedor(proveedor_id)
    return data


@proveedor_router.put(
    "/{proveedor_id}",
    response_model=dict,
    summary="Actualizar proveedor",
    description="Actualiza los datos de un proveedor existente",
    responses={
        200: {"description": "Proveedor actualizado exitosamente"},
        404: {"description": "Proveedor no encontrado"},
        409: {"description": "Email ya existe en otro proveedor"},
        422: {"description": "Error de validación en los datos"}
    }
)
async def actualizar_proveedor(
    proveedor_id: str,
    proveedor: ActualizarProveedorSchema,
    proveedores_service: ProveedoresService = Depends(get_proveedores_service)
):
    """
    Actualiza un proveedor existente.
    
    - Solo se actualizan los campos que se envíen en el request
    - No se puede cambiar el ID tributario ni el país
    - El email debe ser único si se actualiza
    """
    data = await proveedores_service.actualizar_proveedor(
        proveedor_id,
        proveedor.model_dump(exclude_unset=True)
    )
    return data


@proveedor_router.delete(
    "/{proveedor_id}",
    response_model=dict,
    status_code=status.HTTP_200_OK,
    summary="Eliminar proveedor",
    description="Elimina un proveedor del sistema",
    responses={
        200: {"description": "Proveedor eliminado exitosamente"},
        404: {"description": "Proveedor no encontrado"}
    }
)
async def eliminar_proveedor(
    proveedor_id: str,
    proveedores_service: ProveedoresService = Depends(get_proveedores_service)
):
    """
    Elimina un proveedor del sistema.
    
    **Precaución**: Esta operación no se puede deshacer.
    """
    result = await proveedores_service.eliminar_proveedor(proveedor_id)
    return result