from fastapi import APIRouter, Depends, Query, HTTPException
from typing import Optional
import logging

from services.ordenes_queries_service import (
    OrdenesQueriesService,
    get_ordenes_queries_service,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

ordenes_router = APIRouter()


@ordenes_router.get(
    "/",
    summary="Listar órdenes (BFF Web)",
    description="Proxy al servicio de consultas para listar órdenes con filtros y paginación"
)
async def listar_ordenes_bff_web(
    estado: Optional[str] = Query(None, description="Filtrar por estado de la orden"),
    fecha_creacion_desde: Optional[str] = Query(None, description="Fecha de creación desde (ISO)"),
    fecha_creacion_hasta: Optional[str] = Query(None, description="Fecha de creación hasta (ISO)"),
    page: int = Query(1, ge=1, description="Número de página"),
    page_size: int = Query(20, ge=1, le=100, description="Tamaño de página (máx 100)"),
    ordenes_queries_service: OrdenesQueriesService = Depends(get_ordenes_queries_service)
):
    try:
        logger.info("BFF Web: Listando órdenes (estado=%s, page=%s, size=%s)", estado, page, page_size)
        result = await ordenes_queries_service.list_orders(
            estado=estado,
            fecha_creacion_desde=fecha_creacion_desde,
            fecha_creacion_hasta=fecha_creacion_hasta,
            page=page,
            page_size=page_size
        )
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"BFF Web: Error al listar órdenes: {str(e)}")
        raise HTTPException(status_code=500, detail="Error interno del BFF Web al listar órdenes")


