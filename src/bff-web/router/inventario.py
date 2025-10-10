from fastapi import APIRouter, Depends
import logging

from services.inventario_service import InventarioService, get_inventario_service

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

inventario_router = APIRouter()

@inventario_router.get("/health")
def health_check(inventario_service: InventarioService = Depends(get_inventario_service)):
    return inventario_service.health_check()

