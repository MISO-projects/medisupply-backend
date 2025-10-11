from fastapi import APIRouter, Depends
import logging

from services.autenticacion_service import AutenticacionService, get_autenticacion_service

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

autenticacion_router = APIRouter()

@autenticacion_router.get("/health")
def health_check(autenticacion_service: AutenticacionService = Depends(get_autenticacion_service)):
    return autenticacion_service.health_check()

