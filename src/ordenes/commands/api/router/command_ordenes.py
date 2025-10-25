from fastapi import APIRouter, Depends
import logging
from services.order_service import OrderService, get_order_service
from schemas.orden_schema import CrearOrdenSchema
from services.auth_service import get_current_user_id

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

command_ordenes_router = APIRouter()


@command_ordenes_router.post("/")
async def create_order(
    order: CrearOrdenSchema,
    order_service: OrderService = Depends(get_order_service),
    user_id: str = Depends(get_current_user_id)
):
    order_data = order.model_dump(mode='json')
    order_data["creado_por"] = user_id
    
    result = order_service.create_order(order_data)
    return {"id": result["id"], "numero_orden": result["numero_orden"]}
