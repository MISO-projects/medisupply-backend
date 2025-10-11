from fastapi import APIRouter, Depends
import logging

from services.ordenes_commands_service import OrdenesCommandsService, get_ordenes_commands_service

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

ordenes_commands_router = APIRouter()

@ordenes_commands_router.get("/health")
def health_check(ordenes_commands_service: OrdenesCommandsService = Depends(get_ordenes_commands_service)):
    return ordenes_commands_service.health_check()

