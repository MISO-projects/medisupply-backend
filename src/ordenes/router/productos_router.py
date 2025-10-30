from fastapi import APIRouter, Depends, Query, Path
from sqlalchemy.orm import Session
from typing import Optional
import logging

from db.database import get_db
from services.productos_service import ProductosService
from services.init_service import InitService
from schemas.producto_schema import (
    ProductoResponse,
    ProductoCreate,
    ProductoUpdate,
    ProductosListResponse,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

inventario_router = APIRouter()

@inventario_router.post(
    "/",
    response_model=ProductoResponse,
    status_code=201,
    summary="Crear un nuevo producto",
    description="Crea un nuevo producto en el sistema"
)
async def crear_producto(
    producto_data: ProductoCreate,
    db: Session = Depends(get_db)
):
    """Crea un nuevo producto"""
    try:
        logger.info(f"Creando nuevo producto: {producto_data.nombre}")
        
        service = ProductosService(db)
        producto = await service.crear_producto(producto_data)
        
        return ProductoResponse.model_validate(producto)
        
    except Exception as e:
        logger.error(f"Error al crear producto: {str(e)}")
        raise

