from fastapi import FastAPI, Depends, HTTPException
from services.health_service import HealthService, get_health_service
from router.autenticacion import autenticacion_router
from router.clientes import clientes_router
from router.productos import productos_router
from router.ordenes_commands import ordenes_commands_router
from router.ordenes_queries import ordenes_queries_router
import logging

logging.basicConfig(level=logging.DEBUG, force=True)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="MediSupply - BFF Movil",
    description="Backend for Frontend - API Gateway para MediSupply Movil",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    root_path="/movil"
)

app.include_router(autenticacion_router, prefix="/autenticacion", tags=["autenticacion"])
app.include_router(clientes_router, prefix="/clientes", tags=["clientes"])
app.include_router(productos_router, prefix="/productos", tags=["productos"])
app.include_router(ordenes_commands_router, prefix="/ordenes/commands", tags=["ordenes-commands"])
app.include_router(ordenes_queries_router, prefix="/ordenes/queries", tags=["ordenes-queries"])

@app.get("/health")
def health_check(
    details: bool = False,
    health_service: HealthService = Depends(get_health_service)
):
    health_status = health_service.check_overall_health(include_details=details)

    return health_status

