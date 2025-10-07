from fastapi import FastAPI, Depends, HTTPException
from .schemas.orden_schema import CrearOrdenSchema
from .services.order_service import OrderService
from services.health_service import HealthService, get_health_service
import logging


order_service = OrderService()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
app = FastAPI()


@app.get("/health")
def health_check(health_service: HealthService = Depends(get_health_service)):
    health_status = health_service.check_overall_health()

    if health_status["status"] != "healthy":
        raise HTTPException(status_code=503, detail=health_status)

    return health_status


@app.post("/")
async def create_order(order: CrearOrdenSchema):
    result = order_service.create_order(order.model_dump())
    return {"id": result["id"], "numero_orden": result["numero_orden"]}
