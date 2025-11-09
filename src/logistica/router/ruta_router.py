from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from typing import List
import logging
from schemas.ruta_schema import (
    RutaCreateRequest, 
    RutaCreateResponse, 
    RutaResponse,
    RutasListResponse
)
from db.database import get_db
from db.redis_client import RedisClient
from services.ruta_service import RutaService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/rutas", tags=["rutas"])


def get_ruta_service(
    db: Session = Depends(get_db),
    redis_client: RedisClient = Depends(lambda: RedisClient())
) -> RutaService:
    """Dependencia para obtener el servicio de rutas"""
    return RutaService(db=db, redis_client=redis_client)


@router.post(
    "/",
    response_model=RutaCreateResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Crear nueva ruta de entrega",
    description="Crea una nueva ruta de entrega con vehículo, conductor y paradas"
)
def crear_ruta(
    ruta_data: RutaCreateRequest,
    ruta_service: RutaService = Depends(get_ruta_service)
):

    try:
        logger.info(f"Creando nueva ruta para fecha {ruta_data.fecha}")
        resultado = ruta_service.crear_ruta(ruta_data)
        logger.info(f"Ruta creada exitosamente con ID: {resultado.id}")
        return resultado
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error inesperado al crear ruta: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error interno del servidor al crear la ruta"
        )


@router.get(
    "/{ruta_id}",
    response_model=RutaResponse,
    summary="Obtener ruta por ID",
    description="Obtiene los detalles de una ruta específica con todas sus paradas"
)
def obtener_ruta(
    ruta_id: int,
    ruta_service: RutaService = Depends(get_ruta_service)
):
    try:
        logger.info(f"Obteniendo ruta con ID: {ruta_id}")
        return ruta_service.obtener_ruta(ruta_id)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error inesperado al obtener ruta {ruta_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error interno del servidor al obtener la ruta"
        )


@router.get(
    "/",
    response_model=RutasListResponse,
    summary="Listar todas las rutas",
    description="Obtiene una lista de todas las rutas con paginación"
)
def listar_rutas(
    page: int = Query(1, ge=1, description="Número de página"),
    page_size: int = Query(20, ge=1, le=100, description="Tamaño de página (máximo 100)"),
    ruta_service: RutaService = Depends(get_ruta_service)
):
    try:
        logger.info(f"Listando rutas (page={page}, page_size={page_size})")
        
        resultado = ruta_service.listar_rutas(page=page, page_size=page_size)
        
        logger.info(f"Retornando {len(resultado.rutas)} rutas de un total de {resultado.total}")
        
        return resultado
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error inesperado al listar rutas: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error interno del servidor al listar las rutas"
        )


@router.get(
    "/paradas/cliente/{id_cliente}",
    summary="Obtener paradas de entregas por cliente",
    description="Obtiene todas las paradas (entregas programadas) para un cliente específico"
)
def obtener_paradas_por_cliente(
    id_cliente: str,
    estado_parada: str = Query(None, description="Filtrar por estado de parada (Pendiente, En_Camino, Entregada)"),
    estado_ruta: str = Query(None, description="Filtrar por estado de ruta"),
    page: int = Query(1, ge=1, description="Número de página"),
    page_size: int = Query(20, ge=1, le=100, description="Tamaño de página (máximo 100)"),
    ruta_service: RutaService = Depends(get_ruta_service)
):
    """
    Obtiene todas las entregas programadas (paradas) para un cliente específico.
    
    Una entrega programada es una orden que tiene una parada asignada en una ruta de logística.
    """
    try:
        logger.info(f"Obteniendo entregas programadas para cliente {id_cliente}")
        return ruta_service.obtener_entregas_por_cliente(
            id_cliente=id_cliente,
            estado_parada=estado_parada,
            estado_ruta=estado_ruta,
            page=page,
            page_size=page_size
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error al obtener entregas del cliente: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error interno al obtener entregas programadas"
        )

