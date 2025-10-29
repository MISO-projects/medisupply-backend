# src/inventario/router/inventario_router.py

from fastapi import APIRouter, Depends, Query, Path
from sqlalchemy.orm import Session
from typing import Optional
import logging
from http import HTTPStatus

from schemas.inventario_schema import (
    CrearRegistroInventarioSchema, 
    RegistroInventarioResponseSchema, 
    StockDisponibleResponse,
    InventarioListResponse 
)
from typing import List

from services.inventario_service import InventarioService, get_inventario_service

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

inventario_router = APIRouter()


@inventario_router.get(
    "/",
    response_model=InventarioListResponse, 
    summary="Obtener registros de inventario (paginado)",
    description="""
    Retorna una lista paginada de todos los registros de inventario,
    enriquecida con el Nombre y SKU del producto.
    """
)
async def get_registros_inventario_paginado( # ¡async!
    page: int = Query(1, ge=1, description="Número de página"),
    page_size: int = Query(20, ge=1, le=100, description="Tamaño de página (máximo 100)"),
    service: InventarioService = Depends(get_inventario_service)
):
    """
    Endpoint para la tabla de administración web.
    Retorna todos los registros de inventario, con paginación.
    """
    try:
        logger.info(f"Consultando registros de inventario paginados: page={page}, page_size={page_size}")

        skip = (page - 1) * page_size
        
        registros, total = await service.listar_registros_paginados(skip=skip, limit=page_size)
        total_pages = (total + page_size - 1) // page_size if total > 0 else 0
        logger.info(f"Retornando {len(registros)} registros de un total de {total}")
        
        return InventarioListResponse(
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
            items=registros # Pydantic parseará la lista de dicts
        )
        
    except Exception as e:
        logger.error(f"Error en endpoint de registros de inventario: {str(e)}")
        raise

@inventario_router.post(
    "/",
    response_model=RegistroInventarioResponseSchema,
    status_code=HTTPStatus.CREATED
)
def crear_registro(
    data: CrearRegistroInventarioSchema,
    service: InventarioService = Depends(get_inventario_service)
):
    """Crea un nuevo registro de inventario."""
    registro_dict = service.crear_registro_inventario(data)
    return registro_dict

@inventario_router.get(
    "/stock",
    response_model=StockDisponibleResponse,
    status_code=HTTPStatus.OK
)
def listar_stock(
    service: InventarioService = Depends(get_inventario_service)
):
    """
    Obtiene la lista de todos los registros de inventario que tienen stock > 0
    y están disponibles para la venta o reserva.
    """
    stock_disponible = service.listar_stock_disponible()
    
    return StockDisponibleResponse(items=stock_disponible, total=len(stock_disponible))