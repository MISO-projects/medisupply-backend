from fastapi import APIRouter, Depends
import logging

from services.logistica_service import LogisticaService, get_logistica_service

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

logistica_router = APIRouter()

@logistica_router.get("/health")
def health_check(logistica_service: LogisticaService = Depends(get_logistica_service)):
    return logistica_service.health_check()

