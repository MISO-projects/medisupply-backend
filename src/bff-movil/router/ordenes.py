from fastapi import APIRouter, Depends, Query
from typing import Optional
from datetime import datetime
import logging

from services.ordenes_commands_service import OrdenesCommandsService, get_ordenes_commands_service
from services.ordenes_queries_service import OrdenesQueriesService, get_ordenes_queries_service
from services.clientes_service import ClientesService, get_clientes_service

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

ordenes_router = APIRouter()

@ordenes_router.get("/health/commands")
def health_check_commands(ordenes_commands_service: OrdenesCommandsService = Depends(get_ordenes_commands_service)):
    return ordenes_commands_service.health_check()

@ordenes_router.get("/health/queries")
def health_check_queries(ordenes_queries_service: OrdenesQueriesService = Depends(get_ordenes_queries_service)):
    return ordenes_queries_service.health_check()

@ordenes_router.get(
    "/",
    response_model=dict,
    summary="Listar órdenes",
    description="Obtiene listado de órdenes con filtros opcionales y paginación"
)
async def listar_ordenes(
    estado: Optional[str] = Query(None, description="Filtrar por estado de la orden"),
    fecha_creacion_desde: Optional[datetime] = Query(None, description="Fecha de creación desde (ISO format)"),
    fecha_creacion_hasta: Optional[datetime] = Query(None, description="Fecha de creación hasta (ISO format)"),
    page: int = Query(1, ge=1, description="Número de página"),
    page_size: int = Query(20, ge=1, le=100, description="Tamaño de página (máximo 100)"),
    ordenes_queries_service: OrdenesQueriesService = Depends(get_ordenes_queries_service),
    clientes_service: ClientesService = Depends(get_clientes_service)
):
    """
    Lista todas las órdenes con opciones de:
    
    - **Filtros**: Por estado y rango de fecha de creación
    - **Paginación**: Con page (número de página) y page_size (tamaño)
    - **Ordenamiento**: Por fecha de creación (más recientes primero)
    - **Enriquecimiento**: Incluye nombre_cliente para cada orden
    """
    data = await ordenes_queries_service.listar_ordenes(
        estado=estado,
        fecha_creacion_desde=fecha_creacion_desde,
        fecha_creacion_hasta=fecha_creacion_hasta,
        page=page,
        page_size=page_size
    )
    
    orders = data.get("data", [])
    if orders:
        cliente_ids = list(set(order.get("id_cliente") for order in orders if order.get("id_cliente")))
        
        clientes = await clientes_service.get_clientes_by_ids(cliente_ids)
        
        clientes_map = {cliente["id"]: cliente["nombre"] for cliente in clientes}
        
        for order in orders:
            cliente_id = order.get("id_cliente")
            order["nombre_cliente"] = clientes_map.get(cliente_id, "Cliente no encontrado")
    
    return data

@ordenes_router.get(
    "/{order_id}",
    response_model=dict,
    summary="Obtener orden por ID",
    description="Obtiene los detalles completos de una orden específica"
)
async def obtener_orden(
    order_id: str,
    ordenes_queries_service: OrdenesQueriesService = Depends(get_ordenes_queries_service),
    clientes_service: ClientesService = Depends(get_clientes_service)
):
    """
    Obtiene toda la información de una orden específica por su ID.
    Incluye el nombre del cliente enriquecido desde el servicio de clientes.
    """
    # Get order from queries service
    data = await ordenes_queries_service.obtener_orden(order_id)
    
    # Enrich with cliente name
    order = data.get("data", {})
    if order and order.get("id_cliente"):
        clientes = await clientes_service.get_clientes_by_ids([order["id_cliente"]])
        if clientes:
            order["nombre_cliente"] = clientes[0]["nombre"]
        else:
            order["nombre_cliente"] = "Cliente no encontrado"
    
    return data