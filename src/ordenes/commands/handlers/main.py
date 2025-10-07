from .db.database import engine, Base
from fastapi import FastAPI, Request, Depends, HTTPException
from .services.order_handler import OrderHandler
from services.health_service import HealthService, get_health_service
import base64
import json

app = FastAPI()

Base.metadata.create_all(bind=engine)


@app.get("/health")
def health_check(health_service: HealthService = Depends(get_health_service)):
    health_status = health_service.check_overall_health()

    if health_status["status"] != "healthy":
        raise HTTPException(status_code=503, detail=health_status)

    return health_status


@app.post("/")
async def handle_command(request: Request, order_handler: OrderHandler = Depends()):
    envelope = await request.json()
    payload = base64.b64decode(envelope["message"]["data"]).decode("utf-8")
    data = json.loads(payload)

    result = order_handler.handle_order(data)
    return {"data": result, "message": "Order handled successfully"}
