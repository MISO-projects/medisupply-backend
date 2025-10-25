from fastapi import FastAPI, Depends, HTTPException
from services.health_service import HealthService, get_health_service
from router.ruta_router import router as ruta_router
from router.recursos_router import router as recursos_router
from router.conductor_router import router as conductor_router
from router.vehiculo_router import router as vehiculo_router
from db.database import engine, Base
import logging

logging.basicConfig(level=logging.DEBUG, force=True)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="MediSupply Logística Service",
    description="Servicio para gestión de rutas de entrega y logística",
    version="1.0.0"
)

Base.metadata.create_all(bind=engine)
logger.info("Database tables created successfully")

app.include_router(ruta_router)
app.include_router(recursos_router)
app.include_router(conductor_router, prefix="/api/conductores", tags=["Conductores"])
app.include_router(vehiculo_router, prefix="/api/vehiculos", tags=["Vehículos"])


@app.get("/health")
def health_check(health_service: HealthService = Depends(get_health_service)):
    health_status = health_service.check_overall_health()
    
    if health_status["status"] != "healthy":
        raise HTTPException(status_code=503, detail=health_status)
    
    return health_status

