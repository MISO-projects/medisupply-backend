from fastapi import APIRouter, Depends, Query
from typing import Optional
from datetime import datetime
import logging
from ..services.order_service import OrderService

order_service = OrderService()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

order_router = APIRouter()

@order_router.get("/")
async def list_orders(
    estado: Optional[str] = Query(None, description="Filtrar por estado de la orden"),
    fecha_creacion_desde: Optional[datetime] = Query(None, description="Fecha de creación desde (ISO format)"),
    fecha_creacion_hasta: Optional[datetime] = Query(None, description="Fecha de creación hasta (ISO format)"),
    page: int = Query(1, ge=1, description="Número de página"),
    page_size: int = Query(20, ge=1, le=100, description="Tamaño de página (máximo 100)"),
    order_service: OrderService = Depends()
):
    """
    Lista todas las órdenes con opciones de:
    
    - **Filtros**: Por estado y rango de fecha de creación
    - **Paginación**: Con page (número de página) y page_size (tamaño)
    - **Ordenamiento**: Por fecha de creación (más recientes primero)
    """
    skip = (page - 1) * page_size
    
    orders = order_service.list_orders(
        estado=estado,
        fecha_creacion_desde=fecha_creacion_desde,
        fecha_creacion_hasta=fecha_creacion_hasta,
        skip=skip,
        limit=page_size
    )
    
    total = order_service.count_orders(
        estado=estado,
        fecha_creacion_desde=fecha_creacion_desde,
        fecha_creacion_hasta=fecha_creacion_hasta
    )
    
    return {
        "data": orders,
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": (total + page_size - 1) // page_size if total > 0 else 0
    }

@order_router.get("/ids")
async def get_all_order_ids(order_service: OrderService = Depends()):
    data = order_service.get_all_order_ids()
    return {"data": data}

@order_router.get("/{order_id}")
async def get_order(order_id: str, order_service: OrderService = Depends()):
    data = order_service.get_order(order_id)
    return {"data": data}


@order_router.get("/health/cache")
async def get_cache_health(order_service: OrderService = Depends()):
    """Get cache health status and statistics"""
    return order_service.get_cache_health()
