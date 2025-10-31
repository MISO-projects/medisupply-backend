from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session
import logging

from db.database import get_db
from services.vehiculo_service import VehiculoService, get_vehiculo_service
from schemas.vehiculo_schema import (
    VehiculoCreateRequest,
    VehiculoUpdateRequest,
    VehiculoResponse,
    VehiculosListResponse
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter()


@router.post(
    "/",
    response_model=VehiculoResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Crear vehículo",
    description="Crea un nuevo vehículo en el sistema"
)
def crear_vehiculo(
    vehiculo_data: VehiculoCreateRequest,
    vehiculo_service: VehiculoService = Depends(get_vehiculo_service)
):
    logger.info(f"Creando vehículo: {vehiculo_data.placa}")
    return vehiculo_service.crear_vehiculo(vehiculo_data)


@router.get(
    "/{vehiculo_id}",
    response_model=VehiculoResponse,
    summary="Obtener vehículo",
    description="Obtiene un vehículo por su ID"
)
def obtener_vehiculo(
    vehiculo_id: int,
    vehiculo_service: VehiculoService = Depends(get_vehiculo_service)
):
    logger.info(f"Obteniendo vehículo con ID: {vehiculo_id}")
    return vehiculo_service.obtener_vehiculo(vehiculo_id)


@router.get(
    "/",
    response_model=VehiculosListResponse,
    summary="Listar vehículos",
    description="Lista todos los vehículos con paginación"
)
def listar_vehiculos(
    page: int = Query(1, ge=1, description="Número de página"),
    page_size: int = Query(20, ge=1, le=100, description="Tamaño de página"),
    activo: bool = Query(None, description="Filtrar por estado activo/inactivo"),
    vehiculo_service: VehiculoService = Depends(get_vehiculo_service)
):
    logger.info(f"Listando vehículos (page={page}, page_size={page_size}, activo={activo})")
    return vehiculo_service.listar_vehiculos(page=page, page_size=page_size, activo=activo)


@router.put(
    "/{vehiculo_id}",
    response_model=VehiculoResponse,
    summary="Actualizar vehículo",
    description="Actualiza los datos de un vehículo existente"
)
def actualizar_vehiculo(
    vehiculo_id: int,
    vehiculo_data: VehiculoUpdateRequest,
    vehiculo_service: VehiculoService = Depends(get_vehiculo_service)
):
    logger.info(f"Actualizando vehículo con ID: {vehiculo_id}")
    return vehiculo_service.actualizar_vehiculo(vehiculo_id, vehiculo_data)


@router.delete(
    "/{vehiculo_id}",
    summary="Eliminar vehículo",
    description="Desactiva un vehículo (eliminación lógica)"
)
def eliminar_vehiculo(
    vehiculo_id: int,
    vehiculo_service: VehiculoService = Depends(get_vehiculo_service)
):
    logger.info(f"Eliminando vehículo con ID: {vehiculo_id}")
    return vehiculo_service.eliminar_vehiculo(vehiculo_id)

