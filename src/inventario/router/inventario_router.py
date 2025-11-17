# src/inventario/router/inventario_router.py

from fastapi import APIRouter, Depends, Query, Path, HTTPException, Request
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
    DisminuirStockResponseSchema,
    ActualizarInventarioSchema
)
from typing import List

from services.inventario_service import InventarioService, get_inventario_service
from services.auth_dependency import get_current_user

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

inventario_router = APIRouter()


@inventario_router.get(
    "/",
    response_model=InventarioListResponse, 
    summary="Obtener registros de inventario (paginado)",
    description="""
    Retorna una lista paginada de registros de inventario con filtros opcionales.
    Filtros: text_search (busca en nombre, sku, ubicacion), categoria, estado
    Siempre enriquece con nombre y SKU del producto.
    """
)
async def get_registros_inventario_paginado( # ¡async!
    page: int = Query(1, ge=1, description="Número de página"),
    page_size: int = Query(20, ge=1, le=100, description="Tamaño de página (máximo 100)"),
    text_search: Optional[str] = Query(None, description="Buscar en nombre de producto, SKU, o ubicación de inventario"),
    categoria: Optional[str] = Query(None, description="Filtrar por categoría de producto"),
    estado: Optional[str] = Query(None, description="Filtrar por estado de inventario"),
    service: InventarioService = Depends(get_inventario_service)
):
    """
    Endpoint para obtener registros de inventario con filtros opcionales.
    Siempre enriquece con datos de productos.
    """
    try:
        logger.info(
            f"Consultando registros de inventario paginados: page={page}, page_size={page_size}, "
            f"text_search={text_search}, categoria={categoria}, estado={estado}"
        )

        skip = (page - 1) * page_size
        
        registros, total = await service.listar_registros_paginados(
            skip=skip,
            limit=page_size,
            text_search=text_search,
            categoria=categoria,
            estado=estado
        )
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
    request: Request,
    current_user: dict = Depends(get_current_user),
    service: InventarioService = Depends(get_inventario_service)
):
    """Crea un nuevo registro de inventario con auditoría."""
    usuario_id = current_user.get("sub")
    ip_origen = request.client.host if request.client else None
    
    registro_dict = await service.crear_registro_inventario(
        data, 
        usuario_id=usuario_id, 
        ip_origen=ip_origen
    )
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
    request: Request,
    current_user: dict = Depends(get_current_user),
    service: InventarioService = Depends(get_inventario_service)
):
    """
    Disminuye el stock de un producto basado en una solicitud de pedido con auditoría.
    """
    usuario_id = current_user.get("sub")
    ip_origen = request.client.host if request.client else None
    
    result = await service.disminuir_stock_por_pedido(
        data, 
        usuario_id=usuario_id, 
        ip_origen=ip_origen
    )
    return result

@inventario_router.put(
    "/{inventario_id}",
    response_model=RegistroInventarioResponseSchema,
    status_code=HTTPStatus.OK,
    summary="Actualizar registro de inventario",
    description="Actualiza un registro de inventario existente. Registra la operación en auditoría."
)
async def actualizar_registro(
    inventario_id: str = Path(..., description="UUID del registro de inventario"),
    data: ActualizarInventarioSchema = ...,
    request: Request = ...,
    current_user: dict = Depends(get_current_user),
    service: InventarioService = Depends(get_inventario_service)
):
    """
    Actualiza un registro de inventario existente.
    Solo los campos proporcionados serán actualizados.
    Registra todos los cambios en auditoría.
    """
    usuario_id = current_user.get("sub")
    ip_origen = request.client.host if request.client else None
    
    registro_dict = await service.actualizar_registro_inventario(
        inventario_id=inventario_id,
        datos_actualizacion=data,
        usuario_id=usuario_id,
        ip_origen=ip_origen
    )
    return registro_dict

@inventario_router.delete(
    "/{inventario_id}",
    status_code=HTTPStatus.OK,
    summary="Eliminar registro de inventario",
    description="Elimina un registro de inventario. Registra la operación en auditoría con todos los datos del registro."
)
async def eliminar_registro(
    inventario_id: str = Path(..., description="UUID del registro de inventario"),
    request: Request = ...,
    current_user: dict = Depends(get_current_user),
    service: InventarioService = Depends(get_inventario_service)
):
    """
    Elimina un registro de inventario.
    Todos los datos del registro serán guardados en auditoría antes de la eliminación.
    """
    usuario_id = current_user.get("sub")
    ip_origen = request.client.host if request.client else None
    
    result = await service.eliminar_registro_inventario(
        inventario_id=inventario_id,
        usuario_id=usuario_id,
        ip_origen=ip_origen
    )
    return result
