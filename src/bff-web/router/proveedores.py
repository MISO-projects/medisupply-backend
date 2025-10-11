from fastapi import APIRouter, Depends
import logging

from services.proveedores_service import ProveedoresService, get_proveedores_service


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

proveedor_router = APIRouter()



@proveedor_router.get("/health")
def health_check(proveedores_service: ProveedoresService = Depends(get_proveedores_service)):
    return proveedores_service.health_check()