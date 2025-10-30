from fastapi import APIRouter, Depends, HTTPException
from http import HTTPStatus
from typing import List, Dict, Any, Optional
import logging
from schemas.inventario_schema import CrearRegistroInventarioSchema

from services.inventario_service import InventarioService, get_inventario_service

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

inventario_router = APIRouter()

@inventario_router.get("/health")
def health_check(inventario_service: InventarioService = Depends(get_inventario_service)):
    return inventario_service.health_check()

@inventario_router.post(
    "/",
    status_code=201,
    summary="Crear un nuevo registro de inventario",
    description="Crea un nuevo registro de inventario en el sistema"
)
async def crear_registro(
    data: CrearRegistroInventarioSchema,
    service: InventarioService = Depends(get_inventario_service)
):
    """Crea un nuevo registro de inventario."""
    try:
        logger.info(f"BFF Web: Solicitud de creación de registro de inventario - producto_id: {data.producto_id}, cantidad: {data.cantidad}")
        registro_dict = await service.crear_registro_inventario(data.model_dump(mode='json'))
        
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