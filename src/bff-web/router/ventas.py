from fastapi import APIRouter, Depends
import logging

from services.ventas_service import VentasService, get_ventas_service
from router.vendedores import vendedor_router

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

ventas_router = APIRouter()

@ventas_router.get("/health")
def health_check(ventas_service: VentasService = Depends(get_ventas_service)):
    return ventas_service.health_check()

# Incluir el router de vendedores como sub-router
ventas_router.include_router(vendedor_router, prefix="/vendedores", tags=["vendedores"])
# TODO: router de planes de venta
