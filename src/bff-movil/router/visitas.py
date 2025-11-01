# src/bff-movil/router/visitas_router.py

from fastapi import APIRouter, Depends, Query, Path, HTTPException
from typing import Optional, List, Dict
import logging
from datetime import date
from pydantic import UUID4
from http import HTTPStatus

# Importamos los SCHEMAS y el SERVICIO del BFF
from schemas.visitas_schema import (
    CrearRutaVisitaSchema, 
    VisitaResponseSchema,
    RutaVisitaItemSchema,
    VisitaDetalleResponseSchema,
    ActualizarVisitaSchema
)
from services.visitas_service import VisitasService, get_visitas_service

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

visitas_router = APIRouter()


@visitas_router.post(
    "/",
    response_model=VisitaResponseSchema,
    status_code=HTTPStatus.CREATED,
    summary="[BFF] Crear una nueva ruta de visita"
)
async def crear_nueva_ruta_visita(
    data: CrearRutaVisitaSchema, 
    service: VisitasService = Depends(get_visitas_service)
):
    """
    BFF Endpoint para crear una nueva ruta de visita.
    """
    try:
        logger.info(f"BFF Móvil: Solicitud de crear ruta para cliente {data.cliente_id}")
        result = await service.crear_ruta_visita(data)
        logger.info(f"BFF Móvil: Ruta creada con ID {result.get('id')}")
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"BFF Móvil: Error interno al crear ruta: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Error interno del servidor BFF móvil"
        )

@visitas_router.get(
    "/rutas-del-dia",
    response_model=List[RutaVisitaItemSchema],
    summary="[BFF] Obtener las rutas de visita para una fecha y vendedor"
)
async def get_rutas_por_fecha_y_vendedor( 
    fecha: date = Query(..., description="Fecha a consultar en formato YYYY-MM-DD"),
    vendedor_id: UUID4 = Query(..., description="ID del vendedor a consultar"), 
    service: VisitasService = Depends(get_visitas_service)
):
    """
    BFF Endpoint para obtener la lista de rutas de visita.
    """
    try:
        logger.info(f"BFF Móvil: Solicitud de rutas para vendedor {vendedor_id} en fecha {fecha}")
        result = await service.get_rutas_del_dia(fecha, vendedor_id)
        logger.info(f"BFF Móvil: Retornando {len(result)} rutas")
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"BFF Móvil: Error interno al obtener rutas: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Error interno del servidor BFF móvil"
        )
    
@visitas_router.get(
    "/{visita_id}", 
    response_model=VisitaDetalleResponseSchema,
    summary="[BFF] Obtener el detalle de una visita específica"
)
async def get_detalle_visita(
    visita_id: UUID4 = Path(..., description="ID de la visita a consultar"), 
    service: VisitasService = Depends(get_visitas_service)
):
    """
    BFF Endpoint para obtener los detalles completos de una visita.
    """
    try:
        logger.info(f"BFF Móvil: Solicitud de detalle para visita {visita_id}")
        result = await service.get_visita_detalle(visita_id)
        logger.info(f"BFF Móvil: Retornando detalle de visita {visita_id}")
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"BFF Móvil: Error interno al obtener detalle de visita {visita_id}: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Error interno del servidor BFF móvil"
        )
    
@visitas_router.get("/health")
def health_check(productos_service: VisitasService = Depends(get_visitas_service)):
    return productos_service.health_check()

@visitas_router.put(
    "/{visita_id}",
    response_model=VisitaDetalleResponseSchema, 
    summary="[BFF] Actualizar una visita existente"
)
async def actualizar_visita_endpoint(
    data: ActualizarVisitaSchema, 
    visita_id: UUID4 = Path(..., description="ID de la visita a actualizar"), 
    service: VisitasService = Depends(get_visitas_service)
):
    """
    BFF Endpoint para actualizar los detalles de una visita.
    """
    try:
        logger.info(f"BFF Móvil: Solicitud de actualización para visita {visita_id}")
        result = await service.actualizar_visita(visita_id, data)
        logger.info(f"BFF Móvil: Visita {visita_id} actualizada")
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"BFF Móvil: Error interno al actualizar visita {visita_id}: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Error interno del servidor BFF móvil"
        )