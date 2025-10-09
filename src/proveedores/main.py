from fastapi import FastAPI, Depends, HTTPException
from services.health_service import HealthService, get_health_service
from router.proveedor_router import proveedor_router
from db.database import engine, Base
from db.proveedor_model import Proveedor  # Import model to ensure it's registered with Base
import logging

logging.basicConfig(level=logging.DEBUG, force=True)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="MediSupply - Proveedores Service",
    description="API para la gestión de proveedores en MediSupply",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

Base.metadata.create_all(bind=engine)
logger.info("Database tables created successfully")

app.include_router(
    proveedor_router,
    prefix="/proveedores",
    tags=["Proveedores"]
)


@app.get("/health")
def health_check(health_service: HealthService = Depends(get_health_service)):
    health_status = health_service.check_overall_health()
    
    if health_status["status"] != "healthy":
        raise HTTPException(status_code=503, detail=health_status)
    
    return health_status

