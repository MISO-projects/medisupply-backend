from fastapi import APIRouter, Depends, Query, Header, status, HTTPException
from typing import Optional
from datetime import datetime
import logging

from services.ordenes_commands_service import OrdenesCommandsService, get_ordenes_commands_service
from services.ordenes_queries_service import OrdenesQueriesService, get_ordenes_queries_service
from services.clientes_service import ClientesService, get_clientes_service
from services.productos_service import ProductosService, get_productos_service
from services.logistica_service import LogisticaService, get_logistica_service
from services.autenticacion_service import AutenticacionService, get_autenticacion_service
from schemas.orden_schema import (
    CrearOrdenRequest,
    CrearOrdenResponse,
    CrearOrdenClienteRequest,
    PaginadoOrdenes,
    PaginadoOrdenesCliente,
    RespuestaOrden,
    PaginadoEntregasProgramadas,
    IdsResponse,
)

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
    "/ids",
    response_model=IdsResponse,
    summary="Obtener todos los IDs de órdenes",
    description="Obtiene una lista con todos los IDs de órdenes existentes en el sistema"
)
async def obtener_todos_ids_ordenes(
    ordenes_queries_service: OrdenesQueriesService = Depends(get_ordenes_queries_service)
):
    """
    Obtiene todos los IDs de órdenes del sistema.
    
    Útil para operaciones de sincronización, validación o listados rápidos.
    
    Returns:
        IdsResponse: Lista de IDs de órdenes
        
    Raises:
        HTTPException 503: Si el servicio de órdenes no está disponible
    """
    try:
        logger.info("BFF Móvil: Obteniendo todos los IDs de órdenes")
        
        result = await ordenes_queries_service.obtener_todos_ids_ordenes()
        
        logger.info(f"BFF Móvil: {len(result.get('data', []))} IDs de órdenes obtenidos")
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"BFF Móvil: Error al obtener IDs de órdenes: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error inesperado al obtener IDs de órdenes: {str(e)}"
        )

@ordenes_router.post(
    "/",
    response_model=CrearOrdenResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Crear nueva orden",
    description="Crea una nueva orden de compra. El usuario que crea la orden se extrae automáticamente del token JWT."
)
async def crear_orden(
    orden: CrearOrdenRequest,
    ordenes_commands_service: OrdenesCommandsService = Depends(get_ordenes_commands_service),
    authorization: str = Header(..., alias="Authorization")
):
    """
    Crea una nueva orden de compra.
    
    - **observaciones**: Observaciones generales de la orden
    - **id_cliente**: ID del cliente para quien es la orden
    - **id_vendedor**: ID del vendedor asignado
    - **detalles**: Lista de productos con cantidad, precio y observaciones
    
    El campo `creado_por` se extrae automáticamente del token JWT del usuario autenticado.
    La `fecha_entrega_estimada` se calcula automáticamente como 2 días desde la fecha de creación.
    
    Returns:
        CrearOrdenResponse: ID y número de orden generado
    
    Raises:
        HTTPException 401: Si el token JWT es inválido o expiró
        HTTPException 400: Si los datos de la orden son inválidos
        HTTPException 503: Si el servicio de órdenes no está disponible
    """
    try:
        logger.info(f"BFF Móvil: Recibida solicitud para crear orden del cliente {orden.id_cliente}")
        
        # Llamar al servicio de comandos de órdenes pasando el token de autorización
        result = await ordenes_commands_service.create_order(
            order_data=orden.model_dump(mode='json'),
            authorization=authorization
        )
        
        logger.info(f"BFF Móvil: Orden creada exitosamente - {result.get('numero_orden')}")
        return result
        
    except Exception as e:
        logger.error(f"BFF Móvil: Error al crear orden: {str(e)}")
        raise


@ordenes_router.post(
    "/cliente",
    response_model=CrearOrdenResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Crear orden como cliente",
    description="Permite a un cliente crear una orden para sí mismo. El id_cliente y el id_vendedor se obtienen automáticamente."
)
async def crear_orden_cliente(
    orden: CrearOrdenClienteRequest,
    ordenes_commands_service: OrdenesCommandsService = Depends(get_ordenes_commands_service),
    clientes_service: ClientesService = Depends(get_clientes_service),
    authorization: str = Header(..., alias="Authorization")
):
    """
    Crea una nueva orden para un cliente autenticado.
    
    - Requiere autenticación con token JWT de cliente (rol='client')
    - El `id_cliente` se extrae automáticamente del token JWT
    - El `id_vendedor` se obtiene del perfil del cliente
    - Solo requiere observaciones y detalles de la orden
    
    Args:
        orden: Datos de la orden (observaciones y detalles)
        authorization: Token JWT del cliente
    
    Returns:
        CrearOrdenResponse: ID y número de orden generado
    
    Raises:
        HTTPException 401: Si el token JWT es inválido o expiró
        HTTPException 403: Si el usuario no tiene rol 'client'
        HTTPException 400: Si los datos de la orden son inválidos
        HTTPException 404: Si el cliente no tiene vendedor asignado
        HTTPException 503: Si algún servicio no está disponible
    """
    try:
        logger.info("BFF Móvil: Cliente autenticado creando orden")
        
        # 1. Obtener el perfil del cliente para conseguir el id_vendedor
        perfil_cliente = await clientes_service.get_mi_perfil(authorization)
        
        if not perfil_cliente.get("id_vendedor"):
            logger.error(f"Cliente {perfil_cliente.get('id')} no tiene vendedor asignado")
            raise HTTPException(
                status_code=400,
                detail="El cliente no tiene un vendedor asignado. Contacte al administrador."
            )
        
        id_vendedor = perfil_cliente["id_vendedor"]
        logger.info(f"Cliente {perfil_cliente.get('id')} con vendedor {id_vendedor} creando orden")
        
        # 2. Preparar los datos de la orden con el id_vendedor
        order_data = orden.model_dump(mode='json')
        order_data["id_vendedor"] = id_vendedor
        
        # 3. Llamar al servicio de comandos para crear la orden
        # El servicio extraerá el id_cliente del token y lo agregará automáticamente
        result = await ordenes_commands_service.create_client_order(
            order_data=order_data,
            authorization=authorization
        )
        
        logger.info(f"BFF Móvil: Orden de cliente creada exitosamente - {result.get('numero_orden')}")
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"BFF Móvil: Error inesperado al crear orden de cliente: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error inesperado al crear la orden: {str(e)}"
        )

@ordenes_router.get(
    "/",
    response_model=PaginadoOrdenes,
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
    "/mis-ordenes",
    response_model=PaginadoOrdenesCliente,
    summary="Obtener órdenes del cliente autenticado",
    description="Obtiene todas las órdenes del cliente autenticado con paginación"
)
async def obtener_mis_ordenes(
    page: int = Query(1, ge=1, description="Número de página"),
    page_size: int = Query(20, ge=1, le=100, description="Tamaño de página (máximo 100)"),
    ordenes_queries_service: OrdenesQueriesService = Depends(get_ordenes_queries_service),
    authorization: str = Header(..., alias="Authorization")
):
    """
    Obtiene todas las órdenes del cliente autenticado con:
    
    - **Paginación**: Con page (número de página) y page_size (tamaño)
    - **Ordenamiento**: Por fecha de creación (más recientes primero)
    - **Autenticación**: Requiere token JWT con rol 'client'
    
    Returns:
        dict: Respuesta paginada con órdenes del cliente
        
    Raises:
        HTTPException 401: Si el token JWT es inválido o no está presente
        HTTPException 403: Si el usuario no tiene rol 'client'
        HTTPException 503: Si el servicio de órdenes no está disponible
    """
    try:
        logger.info("BFF Móvil: Obteniendo órdenes del cliente autenticado")
        
        # Call the queries service with authorization header
        data = await ordenes_queries_service.obtener_ordenes_cliente(
            authorization=authorization,
            page=page,
            page_size=page_size
        )
        
        logger.info(f"BFF Móvil: Órdenes obtenidas exitosamente - Total: {data.get('total', 0)}")
        return data
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"BFF Móvil: Error al obtener órdenes del cliente: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error inesperado al obtener órdenes: {str(e)}"
        )

@ordenes_router.get(
    "/mis-entregas-programadas",
    response_model=PaginadoEntregasProgramadas,
    summary="Obtener entregas programadas del cliente",
    description="Obtiene todas las entregas que tienen ruta de logística asignada para el cliente autenticado"
)
async def obtener_mis_entregas_programadas(
    estado_parada: Optional[str] = Query(None, description="Filtrar por estado de parada (Pendiente, En_Camino, Entregada)"),
    estado_ruta: Optional[str] = Query(None, description="Filtrar por estado de ruta"),
    page: int = Query(1, ge=1, description="Número de página"),
    page_size: int = Query(20, ge=1, le=100, description="Tamaño de página (máximo 100)"),
    logistica_service: LogisticaService = Depends(get_logistica_service),
    autenticacion_service: AutenticacionService = Depends(get_autenticacion_service),
    authorization: str = Header(..., alias="Authorization")
):
    """
    Obtiene todas las entregas programadas del cliente autenticado.
    
    Una entrega programada es una orden que tiene asignada una ruta de logística
    con fecha, conductor y vehículo para su entrega.
    
    - **Autenticación**: Requiere token JWT con rol 'client'
    - **Filtros**: Por estado de parada y estado de ruta
    - **Paginación**: Con page y page_size
    
    Returns:
        dict: Entregas programadas con información de la orden, parada y ruta
        
    Raises:
        HTTPException 401: Si el token JWT es inválido o no está presente
        HTTPException 403: Si el usuario no tiene rol 'client'
        HTTPException 503: Si el servicio de logística no está disponible
    """
    try:
        logger.info("BFF Móvil: Obteniendo entregas programadas del cliente")
        
        # Extraer el token del header Authorization
        if not authorization or not authorization.lower().startswith("bearer "):
            raise HTTPException(
                status_code=401,
                detail="Token de autorización requerido con formato 'Bearer <token>'"
            )
        
        token = authorization[7:].strip()  # Remover 'Bearer ' del inicio
        
        # Obtener el perfil del usuario a partir del token
        perfil = await autenticacion_service.get_current_user(token)
        
        if perfil.get("role") != "client":
            raise HTTPException(
                status_code=403,
                detail="Acceso denegado. Solo clientes pueden ver sus entregas programadas"
            )
        
        id_cliente = perfil.get("id_client")
        
        if not id_cliente:
            raise HTTPException(
                status_code=401,
                detail="Token no contiene id_client"
            )
        
        # Consultar el servicio de logística
        entregas = await logistica_service.obtener_entregas_programadas_cliente(
            id_cliente=id_cliente,
            estado_parada=estado_parada,
            estado_ruta=estado_ruta,
            page=page,
            page_size=page_size
        )
        
        logger.info(f"BFF Móvil: {entregas.get('total', 0)} entregas programadas encontradas")
        return entregas
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"BFF Móvil: Error al obtener entregas programadas: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error inesperado al obtener entregas programadas: {str(e)}"
        )

@ordenes_router.get(
    "/{order_id}",
    response_model=RespuestaOrden,
    summary="Obtener orden por ID",
    description="Obtiene los detalles completos de una orden específica"
)
async def obtener_orden(
    order_id: str,
    ordenes_queries_service: OrdenesQueriesService = Depends(get_ordenes_queries_service),
    clientes_service: ClientesService = Depends(get_clientes_service),
    productos_service: ProductosService = Depends(get_productos_service)
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
            order["direccion_cliente"] = clientes[0]["address"]
        else:
            order["nombre_cliente"] = "Cliente no encontrado"
            order["direccion_cliente"] = "Dirección no encontrada"

    # Enrich each detalle with product name
    detalles = order.get("detalles") if order else None
    if detalles:
        producto_ids = list({d.get("id_producto") for d in detalles if d.get("id_producto")})
        if producto_ids:
            productos = await productos_service.get_productos_by_ids(producto_ids)
            productos_map = {p.get("id"): p.get("nombre") for p in productos}
            for d in detalles:
                pid = d.get("id_producto")
                if pid:
                    d["nombre_producto"] = productos_map.get(pid, "Producto no encontrado")
    
    return data