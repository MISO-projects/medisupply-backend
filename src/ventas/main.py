from fastapi import FastAPI, Depends, HTTPException
from services.health_service import HealthService, get_health_service
from router.vendedor_router import vendedor_router
from db.database import engine, Base
from db.vendedor_model import Vendedor  # Importar el modelo para registrarlo con Base
import logging

logging.basicConfig(level=logging.DEBUG, force=True)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="MediSupply - Ventas Service",
    description="API para la gestión de vendedores en MediSupply",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Crear las tablas en la base de datos
Base.metadata.create_all(bind=engine)
logger.info("Database tables created successfully")

# Registrar el router de vendedores
app.include_router(
    vendedor_router,
    prefix="/vendedores",
    tags=["Vendedores"]
)


@app.get("/health")
def health_check(health_service: HealthService = Depends(get_health_service)):
    health_status = health_service.check_overall_health()

    if health_status["status"] != "healthy":
        raise HTTPException(status_code=503, detail=health_status)

    return health_status

