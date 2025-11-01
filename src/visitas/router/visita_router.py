# src/visitas/router/visita_router.py

from fastapi import APIRouter, Depends, Query, Path, HTTPException
from sqlalchemy.orm import Session
from typing import Optional, List, Dict
import logging
from http import HTTPStatus

from schemas.visita_schema import (
    CrearRutaVisitaSchema, 
    VisitaResponseSchema
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

# ... (Tus otros endpoints) ...