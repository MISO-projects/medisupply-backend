from fastapi import APIRouter, Depends, status
import logging
from services.order_service import OrderService, get_order_service
from schemas.orden_schema import CrearOrdenSchema, CrearOrdenClienteSchema
from services.auth_service import get_current_user_id, get_current_client_id

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

command_ordenes_router = APIRouter()


@command_ordenes_router.post("/")
async def create_order(
    order: CrearOrdenSchema,
    order_service: OrderService = Depends(get_order_service),
    user_id: str = Depends(get_current_user_id)
):
    """
    Crear orden (para usuarios internos/vendedores)
    
    Requiere autenticación con token de usuario interno.
    """
    order_data = order.model_dump(mode='json')
    order_data["creado_por"] = user_id
    
    result = order_service.create_order(order_data)
    return {"id": result["id"], "numero_orden": result["numero_orden"]}


@command_ordenes_router.post(
    "/cliente",
    status_code=status.HTTP_201_CREATED,
    summary="Crear orden como cliente",
    description="Permite a un cliente crear una orden para sí mismo. El id_cliente se extrae del token JWT."
)
async def create_client_order(
    order: CrearOrdenClienteSchema,
    order_service: OrderService = Depends(get_order_service),
    client_id: str = Depends(get_current_client_id)
):
    """
    Crear orden (para clientes)
    
    - Requiere autenticación con token de cliente (rol='client')
    - El `id_cliente` se extrae automáticamente del token JWT
    - El cliente solo puede crear órdenes para sí mismo
    
    Returns:
        dict: ID y número de orden generado
        
    Raises:
        HTTPException 401: Si el token JWT es inválido o expiró
        HTTPException 403: Si el usuario no tiene rol 'client'
        HTTPException 400: Si los datos de la orden son inválidos
    """
    logger.info(f"Cliente {client_id} creando orden")
    
    # Convertir el schema a dict y agregar el id_cliente del token
    order_data = order.model_dump(mode='json')
    order_data["id_cliente"] = client_id
    order_data["creado_por"] = client_id  # El cliente es quien crea la orden
    
    result = order_service.create_order(order_data)
    
    logger.info(f"Orden {result['numero_orden']} creada exitosamente para cliente {client_id}")
    return {"id": result["id"], "numero_orden": result["numero_orden"]}
