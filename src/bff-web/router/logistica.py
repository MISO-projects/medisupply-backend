from fastapi import APIRouter, Depends, Body, Query
from typing import Dict, Any, List
import logging

from services.logistica_service import LogisticaService, get_logistica_service

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

logistica_router = APIRouter()


@logistica_router.get("/health")
def health_check(logistica_service: LogisticaService = Depends(get_logistica_service)):

    return logistica_service.health_check()


@logistica_router.post(
    "/rutas",
    status_code=201,
    summary="Crear nueva ruta de entrega",
    description="Crea una nueva ruta de entrega con vehículo, conductor y paradas"
)
def crear_ruta(
    ruta_data: Dict[str, Any] = Body(
        ...,
        example={
            "fecha": "2025-08-17",
            "bodega_origen": "Central Bogotá",
            "estado": "Pendiente",
            "vehiculo_id": 12,
            "conductor_id": 4,
            "condiciones_almacenamiento": "Refrigerado",
            "paradas": [
                {
                    "cliente_id": 32,
                    "direccion": "Calle 80 #45-20",
                    "contacto": "Carlos Ríos",
                    "latitud": 4.7110,
                    "longitud": -74.0721
                },
                {
                    "cliente_id": 15,
                    "direccion": "Av. 30 #22-10",
                    "contacto": "María López",
                    "latitud": 4.6097,
                    "longitud": -74.0817
                }
            ]
        }
    ),
    logistica_service: LogisticaService = Depends(get_logistica_service)
):

    logger.info(f"BFF-Web: Creando nueva ruta para fecha {ruta_data.get('fecha')}")
    return logistica_service.crear_ruta(ruta_data)


@logistica_router.get(
    "/rutas/{ruta_id}",
    summary="Obtener ruta por ID",
    description="Obtiene los detalles completos de una ruta específica"
)
def obtener_ruta(
    ruta_id: int,
    logistica_service: LogisticaService = Depends(get_logistica_service)
):

    logger.info(f"BFF-Web: Obteniendo ruta {ruta_id}")
    return logistica_service.obtener_ruta(ruta_id)


@logistica_router.get(
    "/rutas",
    summary="Listar todas las rutas",
    description="Obtiene una lista de todas las rutas con paginación"
)
def listar_rutas(
    page: int = Query(1, ge=1, description="Número de página"),
    page_size: int = Query(20, ge=1, le=100, description="Tamaño de página (máximo 100)"),
    logistica_service: LogisticaService = Depends(get_logistica_service)
):

    logger.info(f"BFF-Web: Listando rutas (page={page}, page_size={page_size})")
    return logistica_service.listar_rutas(page=page, page_size=page_size)


@logistica_router.post(
    "/conductores",
    status_code=201,
    summary="Crear conductor",
    description="Crea un nuevo conductor en el sistema"
)
def crear_conductor(
    conductor_data: Dict[str, Any] = Body(...),
    logistica_service: LogisticaService = Depends(get_logistica_service)
):
    """Crea un nuevo conductor"""
    logger.info(f"BFF-Web: Creando conductor")
    return logistica_service.crear_conductor(conductor_data)


@logistica_router.get(
    "/conductores/{conductor_id}",
    summary="Obtener conductor",
    description="Obtiene un conductor por su ID"
)
def obtener_conductor(
    conductor_id: int,
    logistica_service: LogisticaService = Depends(get_logistica_service)
):
    logger.info(f"BFF-Web: Obteniendo conductor {conductor_id}")
    return logistica_service.obtener_conductor(conductor_id)


@logistica_router.get(
    "/conductores",
    summary="Listar conductores",
    description="Lista todos los conductores con paginación"
)
def listar_conductores(
    page: int = Query(1, ge=1, description="Número de página"),
    page_size: int = Query(20, ge=1, le=100, description="Tamaño de página"),
    activo: bool = Query(None, description="Filtrar por estado activo/inactivo"),
    logistica_service: LogisticaService = Depends(get_logistica_service)
):
    """Lista todos los conductores"""
    logger.info(f"BFF-Web: Listando conductores (page={page}, page_size={page_size}, activo={activo})")
    return logistica_service.listar_conductores(page=page, page_size=page_size, activo=activo)


@logistica_router.put(
    "/conductores/{conductor_id}",
    summary="Actualizar conductor",
    description="Actualiza los datos de un conductor"
)
def actualizar_conductor(
    conductor_id: int,
    conductor_data: Dict[str, Any] = Body(...),
    logistica_service: LogisticaService = Depends(get_logistica_service)
):
    """Actualiza un conductor"""
    logger.info(f"BFF-Web: Actualizando conductor {conductor_id}")
    return logistica_service.actualizar_conductor(conductor_id, conductor_data)


@logistica_router.delete(
    "/conductores/{conductor_id}",
    summary="Eliminar conductor",
    description="Desactiva un conductor"
)
def eliminar_conductor(
    conductor_id: int,
    logistica_service: LogisticaService = Depends(get_logistica_service)
):
    """Elimina (desactiva) un conductor"""
    logger.info(f"BFF-Web: Eliminando conductor {conductor_id}")
    return logistica_service.eliminar_conductor(conductor_id)


@logistica_router.post(
    "/vehiculos",
    status_code=201,
    summary="Crear vehículo",
    description="Crea un nuevo vehículo en el sistema"
)
def crear_vehiculo(
    vehiculo_data: Dict[str, Any] = Body(...),
    logistica_service: LogisticaService = Depends(get_logistica_service)
):
    logger.info(f"BFF-Web: Creando vehículo")
    return logistica_service.crear_vehiculo(vehiculo_data)


@logistica_router.get(
    "/vehiculos/{vehiculo_id}",
    summary="Obtener vehículo",
    description="Obtiene un vehículo por su ID"
)
def obtener_vehiculo(
    vehiculo_id: int,
    logistica_service: LogisticaService = Depends(get_logistica_service)
):
    logger.info(f"BFF-Web: Obteniendo vehículo {vehiculo_id}")
    return logistica_service.obtener_vehiculo(vehiculo_id)


@logistica_router.get(
    "/vehiculos",
    summary="Listar vehículos",
    description="Lista todos los vehículos con paginación"
)
def listar_vehiculos(
    page: int = Query(1, ge=1, description="Número de página"),
    page_size: int = Query(20, ge=1, le=100, description="Tamaño de página"),
    activo: bool = Query(None, description="Filtrar por estado activo/inactivo"),
    logistica_service: LogisticaService = Depends(get_logistica_service)
):
    logger.info(f"BFF-Web: Listando vehículos (page={page}, page_size={page_size}, activo={activo})")
    return logistica_service.listar_vehiculos(page=page, page_size=page_size, activo=activo)


@logistica_router.put(
    "/vehiculos/{vehiculo_id}",
    summary="Actualizar vehículo",
    description="Actualiza los datos de un vehículo"
)
def actualizar_vehiculo(
    vehiculo_id: int,
    vehiculo_data: Dict[str, Any] = Body(...),
    logistica_service: LogisticaService = Depends(get_logistica_service)
):
    logger.info(f"BFF-Web: Actualizando vehículo {vehiculo_id}")
    return logistica_service.actualizar_vehiculo(vehiculo_id, vehiculo_data)


@logistica_router.delete(
    "/vehiculos/{vehiculo_id}",
    summary="Eliminar vehículo",
    description="Desactiva un vehículo"
)
def eliminar_vehiculo(
    vehiculo_id: int,
    logistica_service: LogisticaService = Depends(get_logistica_service)
):
    logger.info(f"BFF-Web: Eliminando vehículo {vehiculo_id}")
    return logistica_service.eliminar_vehiculo(vehiculo_id)
