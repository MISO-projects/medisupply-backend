from fastapi import FastAPI, Depends, HTTPException
from .services.order_service import OrderService
from services.health_service import HealthService, get_health_service
import logging
from .router.command_ordenes import command_ordenes_router


order_service = OrderService()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
app = FastAPI()

app.include_router(command_ordenes_router, prefix="/ordenes", tags=["ordenes-commands"])

@app.get("/health")
def health_check(health_service: HealthService = Depends(get_health_service)):
    health_status = health_service.check_overall_health()

    if health_status["status"] != "healthy":
        raise HTTPException(status_code=503, detail=health_status)

    return health_status


