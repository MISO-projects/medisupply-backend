from fastapi import APIRouter, Depends
import logging
from ..services.order_service import OrderService

order_service = OrderService()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

order_router = APIRouter()

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
