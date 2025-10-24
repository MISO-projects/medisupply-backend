from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session
import logging

from db.database import get_db
from services.conductor_service import ConductorService, get_conductor_service
from schemas.conductor_schema import (
    ConductorCreateRequest,
    ConductorUpdateRequest,
    ConductorResponse,
    ConductoresListResponse
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter()


@router.post(
    "/",
    response_model=ConductorResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Crear conductor",
    description="Crea un nuevo conductor en el sistema"
)
def crear_conductor(
    conductor_data: ConductorCreateRequest,
    conductor_service: ConductorService = Depends(get_conductor_service)
):
    logger.info(f"Creando conductor: {conductor_data.nombre} {conductor_data.apellido}")
    return conductor_service.crear_conductor(conductor_data)


@router.get(
    "/{conductor_id}",
    response_model=ConductorResponse,
    summary="Obtener conductor",
    description="Obtiene un conductor por su ID"
)
def obtener_conductor(
    conductor_id: int,
    conductor_service: ConductorService = Depends(get_conductor_service)
):
    logger.info(f"Obteniendo conductor con ID: {conductor_id}")
    return conductor_service.obtener_conductor(conductor_id)


@router.get(
    "/",
    response_model=ConductoresListResponse,
    summary="Listar conductores",
    description="Lista todos los conductores con paginación"
)
def listar_conductores(
    page: int = Query(1, ge=1, description="Número de página"),
    page_size: int = Query(20, ge=1, le=100, description="Tamaño de página"),
    activo: bool = Query(None, description="Filtrar por estado activo/inactivo"),
    conductor_service: ConductorService = Depends(get_conductor_service)
):
    logger.info(f"Listando conductores (page={page}, page_size={page_size}, activo={activo})")
    return conductor_service.listar_conductores(page=page, page_size=page_size, activo=activo)


@router.put(
    "/{conductor_id}",
    response_model=ConductorResponse,
    summary="Actualizar conductor",
    description="Actualiza los datos de un conductor existente"
)
def actualizar_conductor(
    conductor_id: int,
    conductor_data: ConductorUpdateRequest,
    conductor_service: ConductorService = Depends(get_conductor_service)
):
    logger.info(f"Actualizando conductor con ID: {conductor_id}")
    return conductor_service.actualizar_conductor(conductor_id, conductor_data)


@router.delete(
    "/{conductor_id}",
    summary="Eliminar conductor",
    description="Desactiva un conductor (eliminación lógica)"
)
def eliminar_conductor(
    conductor_id: int,
    conductor_service: ConductorService = Depends(get_conductor_service)
):
    logger.info(f"Eliminando conductor con ID: {conductor_id}")
    return conductor_service.eliminar_conductor(conductor_id)

