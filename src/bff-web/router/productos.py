from fastapi import APIRouter, Depends
import logging

from services.productos_service import ProductosService, get_productos_service

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

productos_router = APIRouter()

@productos_router.get("/health")
def health_check(productos_service: ProductosService = Depends(get_productos_service)):
    return productos_service.health_check()

