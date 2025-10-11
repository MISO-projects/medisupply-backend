from fastapi import APIRouter, Depends
import logging

from services.reportes_service import ReportesService, get_reportes_service

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

reportes_router = APIRouter()

@reportes_router.get("/health")
def health_check(reportes_service: ReportesService = Depends(get_reportes_service)):
    return reportes_service.health_check()

