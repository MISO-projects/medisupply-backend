# src/inventario/router/inventario_router.py

from fastapi import APIRouter, Depends, Query, Path, HTTPException
from sqlalchemy.orm import Session
from typing import Optional, List, Dict
import logging
from http import HTTPStatus

from schemas.inventario_schema import (
    CrearRegistroInventarioSchema, 
    RegistroInventarioResponseSchema, 
    StockDisponibleResponse,
    InventarioListResponse,
    StockBatchRequest, 
    StockBatchResponse,
    CrearRegistroPedidoSchema,
    DisminuirStockResponseSchema
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
async def crear_registro(
    data: CrearRegistroInventarioSchema,
    service: InventarioService = Depends(get_inventario_service)
):
    """Crea un nuevo registro de inventario."""
    registro_dict = await service.crear_registro_inventario(data)
    return registro_dict

@inventario_router.post(
    "/stock/batch", 
    response_model=StockBatchResponse,
    summary="Obtener stock agregado para múltiples productos"
)
def get_stock_batch(
    request: StockBatchRequest,
    service: InventarioService = Depends(get_inventario_service)
):
    try:
        stock_map = service.get_stock_agregado_por_ids(request.producto_ids)
        return {"stock_data": stock_map}
    except Exception as e:
        logger.error(f"Error en endpoint de stock batch: {str(e)}")
        raise HTTPException(status_code=500, detail="Error al obtener el stock agregado.")
    
@inventario_router.put(
    "/registro/pedido",
    response_model=DisminuirStockResponseSchema,
    status_code=HTTPStatus.OK,  
    summary="Disminuir stock por pedido (FIFO/FEFO)", 
    description="""
    Disminuye la cantidad de un producto en el inventario,
    siguiendo la lógica de FIFO/FEFO (First-Expired, First-Out).
    Primero consume lotes próximos a vencer, luego lotes más antiguos.
    """
)
async def disminuir_stock_por_pedido( 
    data: CrearRegistroPedidoSchema,
    service: InventarioService = Depends(get_inventario_service)
):
    """
    Disminuye el stock de un producto basado en una solicitud de pedido.
    """
    result = await service.disminuir_stock_por_pedido(data)
    return result
