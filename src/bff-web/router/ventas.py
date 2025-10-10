from fastapi import APIRouter, Depends
import logging

from services.ventas_service import VentasService, get_ventas_service

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

ventas_router = APIRouter()

@ventas_router.get("/health")
def health_check(ventas_service: VentasService = Depends(get_ventas_service)):
    return ventas_service.health_check()

