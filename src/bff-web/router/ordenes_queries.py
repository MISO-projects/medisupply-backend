from fastapi import APIRouter, Depends
import logging

from services.ordenes_queries_service import OrdenesQueriesService, get_ordenes_queries_service

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

ordenes_queries_router = APIRouter()

@ordenes_queries_router.get("/health")
def health_check(ordenes_queries_service: OrdenesQueriesService = Depends(get_ordenes_queries_service)):
    return ordenes_queries_service.health_check()

