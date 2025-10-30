from fastapi import APIRouter, Depends, HTTPException, Query, Header # ¡MODIFICADO!
from http import HTTPStatus
from typing import List, Dict, Any, Optional
import logging
from schemas.inventario_schema import CrearRegistroInventarioSchema, InventarioListResponse

from services.inventario_service import InventarioService, get_inventario_service

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

inventario_router = APIRouter()

@inventario_router.get("/health")
def health_check(inventario_service: InventarioService = Depends(get_inventario_service)):
    return inventario_service.health_check()

@inventario_router.get(
    "/",
    response_model=InventarioListResponse,
    summary="Listar registros de inventario (paginado)",
    description="Obtiene la lista paginada de registros de inventario para la tabla web."
)
async def listar_registros(
    page: int = Query(1, ge=1, description="Número de página"),
    page_size: int = Query(20, ge=1, le=100, description="Tamaño de página"),
    service: InventarioService = Depends(get_inventario_service),
    authorization: str = Header(..., alias="Authorization")
):
    """
    Endpoint del BFF para obtener la lista paginada de inventario.
    """
    try:
        logger.info(f"BFF Web: Solicitando lista de inventario (página {page}).")
        response_data = await service.listar_registros_inventario(
            page=page,
            page_size=page_size,
            token=authorization
        )
        return response_data
        
    except HTTPException:
        raise 
    except Exception as e:
        logger.error(f"BFF Web: Error interno al listar inventario: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Error interno del servidor BFF web"
        )


@inventario_router.post(
    "/",
    status_code=201,
    summary="Crear un nuevo registro de inventario",
    description="Crea un nuevo registro de inventario en el sistema"
)
async def crear_registro(
    data: CrearRegistroInventarioSchema,
    service: InventarioService = Depends(get_inventario_service),
    authorization: str = Header(..., alias="Authorization")
):
    """Crea un nuevo registro de inventario."""
    try:
        logger.info("BFF Web: Solicitud de creación de registro de inventario.")
        registro_dict = await service.crear_registro_inventario(
            data.model_dump(mode='json'),
            token=authorization
        )
        
        logger.info(f"BFF Web: Registro de inventario creado exitosamente - ID: {registro_dict.get('id')}")
        return registro_dict        
    except HTTPException:
        raise      
    except Exception as e:
        logger.error(f"BFF Web: Error interno al procesar solicitud de creación de registro de inventario: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Error interno del servidor BFF web"
        )   