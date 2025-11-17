from fastapi import APIRouter, Depends, Query, Path, HTTPException
from sqlalchemy.orm import Session
from typing import Optional, List, Dict
import logging
from datetime import date
from pydantic import UUID4
from http import HTTPStatus

from schemas.visita_schema import (
    CrearRutaVisitaSchema, 
    VisitaResponseSchema,
    RutaVisitaItemSchema,
    VisitaDetalleResponseSchema,
    ActualizarVisitaSchema
)
from typing import List

from services.visita_service import VisitaService, get_visita_service

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

visita_router = APIRouter()


@visita_router.post(
    "/",
    response_model=VisitaResponseSchema,
    status_code=HTTPStatus.CREATED,
    summary="Crear una nueva ruta de visita (Auto-asignando vendedor)", 
    description="""
    Crea un registro de visita programada.
    Solo requiere el `cliente_id`.
    El `vendedor_id` se obtiene automáticamente del microservicio de Clientes.
    La fecha se asigna a las 00:00 UTC del día hábil.
    """ 
)
async def crear_nueva_ruta_visita(
    data: CrearRutaVisitaSchema, 
    service: VisitaService = Depends(get_visita_service)
):
    """
    Crea un nuevo registro de ruta de visita.
    El body solo requiere `cliente_id`.
    El `vendedor_id` se consulta internamente.
    La `fecha_visita_programada` se genera automáticamente.
    """
    try:
        visita_dict = await service.crear_ruta_visita(data)
        return visita_dict 
    except HTTPException as he:
        raise he
    except Exception as e:
        logger.error(f"Error inesperado en endpoint POST /visita: {str(e)}")
        raise HTTPException(
            status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
            detail=f"Error inesperado al crear la ruta: {str(e)}"
        )

@visita_router.get(
    "/rutas-del-dia",
    response_model=List[RutaVisitaItemSchema],
    summary="Obtener la ruta de visitas optimizada del día", 
    description="""
    Obtiene todas las visitas PENDIENTES para una fecha y vendedor.
    Si se proveen 'lat_actual' y 'lon_actual', la lista vendrá
    optimizada por ruta (Google Maps) y el campo 'hora_de_la_cita'
    contendrá el tiempo de viaje (ej: "15 min").
    Si no se proveen, listará las visitas pendientes del día (sin optimizar).
    """ 
)
async def get_rutas_por_fecha_y_vendedor( 
    fecha: date = Query(..., description="Fecha a consultar en formato YYYY-MM-DD"),
    vendedor_id: UUID4 = Query(..., description="ID del vendedor a consultar"),
    lat_actual: Optional[float] = Query(None, description="Latitud actual del vendedor para optimizar ruta"),
    lon_actual: Optional[float] = Query(None, description="Longitud actual del vendedor para optimizar ruta"),
    service: VisitaService = Depends(get_visita_service)
):
    """
    Obtiene la lista de rutas de visita, optimizada si se provee ubicación.
    """
    try:
        rutas = await service.get_rutas_por_fecha_y_vendedor(
            fecha=fecha, 
            vendedor_id=vendedor_id,
            lat_actual=lat_actual,
            lon_actual=lon_actual 
        )
        return rutas
    except HTTPException as he:
        raise he
    except Exception as e:
        logger.error(f"Error inesperado en endpoint GET /rutas-del-dia: {str(e)}")
        raise HTTPException(
            status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
            detail=f"Error inesperado al obtener las rutas: {str(e)}"
        )
    
@visita_router.get(
    "/{visita_id}", 
    response_model=VisitaDetalleResponseSchema,
    summary="Obtener el detalle de una visita específica",
    description="""
    Obtiene toda la información almacenada de una visita,
    dado su ID. Además, enriquece la respuesta con
    el nombre, dirección, notas anteriores y productos preferidos.
    """
)
async def get_detalle_visita(
    visita_id: UUID4 = Path(..., description="ID de la visita a consultar"), 
    lat_actual: Optional[float] = Query(None, description="Latitud actual del vendedor"),
    lon_actual: Optional[float] = Query(None, description="Longitud actual del vendedor"),
    service: VisitaService = Depends(get_visita_service)
):
    """
    Obtiene los detalles completos de una visita por su ID.
    """
    try:
        visita_detalle = await service.get_visita_detalle_por_id(visita_id,lat_actual=lat_actual,lon_actual=lon_actual)
        return visita_detalle
    except HTTPException as he:
        raise he
    except Exception as e:
        logger.error(f"Error inesperado en endpoint GET /visita/{visita_id}: {str(e)}")
        raise HTTPException(
            status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
            detail=f"Error inesperado al obtener la visita: {str(e)}"
        )
    
@visita_router.put(
    "/{visita_id}",
    response_model=VisitaDetalleResponseSchema, 
    summary="Actualizar una visita existente",
    description="""
    Actualiza uno o más campos de una visita.
    Ideal para marcar una visita como 'REALIZADA' y registrar
    el detalle, la evidencia (URL), y las horas de inicio/fin.
    """
)
async def actualizar_visita_endpoint(
    data: ActualizarVisitaSchema, 
    visita_id: UUID4 = Path(..., description="ID de la visita a actualizar"), 
    service: VisitaService = Depends(get_visita_service)
):
    """
    Actualiza los detalles de una visita específica por su ID.
    """
    try:
        visita_actualizada = await service.actualizar_visita(visita_id, data)
        return visita_actualizada
    except HTTPException as he:
        raise he
    except Exception as e:
        logger.error(f"Error inesperado en endpoint PUT /visita/{visita_id}: {str(e)}")
        raise HTTPException(
            status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
            detail=f"Error inesperado al actualizar la visita: {str(e)}"
        )