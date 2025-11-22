from db.database import engine, Base
from fastapi import FastAPI, Request, Depends, HTTPException
from services.order_projection_handler import OrderProjectionHandler
from services.health_service import HealthService, get_health_service
import base64
import json
import logging

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()

Base.metadata.create_all(bind=engine)

@app.get("/health")
def health_check(health_service: HealthService = Depends(get_health_service)):
    health_status = health_service.check_overall_health()

    if health_status["status"] != "healthy":
        raise HTTPException(status_code=503, detail=health_status)

    return health_status


@app.get("/test")
async def test_endpoint():
    """Endpoint de prueba para verificar que el servicio está accesible"""
    logger.info("Test endpoint called")
    return {"status": "ok", "service": "order-query-projection"}


@app.post("/")
async def create_projection(
    request: Request, order_projection_handler: OrderProjectionHandler = Depends()
):
    try:
        logger.info("Received push notification from Pub/Sub")
        envelope = await request.json()
        logger.info(f"Envelope received: {envelope}")
        
        payload = base64.b64decode(envelope["message"]["data"]).decode("utf-8")
        logger.info(f"Decoded payload: {payload}")
        
        data = json.loads(payload)
        logger.info(f"Parsed order data: {data.get('id', 'N/A')}")

        result = order_projection_handler.handle_order_created_event(data)
        logger.info(f"Projection created successfully for order: {result.get('numero_orden', 'N/A')}")
        
        return {"data": result, "message": "Order handled successfully"}
    except Exception as e:
        logger.error(f"Error creating projection: {str(e)}", exc_info=True)
        # Return 200 to avoid Pub/Sub retries for unrecoverable errors
        return {"error": str(e), "message": "Error processing order projection"}
