from fastapi import APIRouter, Depends
import logging

from services.clientes_service import ClientesService, get_clientes_service

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

clientes_router = APIRouter()

@clientes_router.get("/health")
def health_check(clientes_service: ClientesService = Depends(get_clientes_service)):
    return clientes_service.health_check()

