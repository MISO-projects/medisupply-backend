from fastapi import APIRouter, Depends
import logging

from services.auditoria_service import AuditoriaService, get_auditoria_service

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

auditoria_router = APIRouter()

@auditoria_router.get("/health")
def health_check(auditoria_service: AuditoriaService = Depends(get_auditoria_service)):
    return auditoria_service.health_check()

