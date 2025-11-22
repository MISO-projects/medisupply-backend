from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends, HTTPException
from services.health_service import HealthService, get_health_service
from router.auditoria_router import auditoria_router
from db.database import engine, Base
from db import models  # Importar modelos para que se registren

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Crear tablas al inicio
    Base.metadata.create_all(bind=engine)
    yield

app = FastAPI(
    title="Auditoría Service API",
    description="Servicio de auditoría y detección de patrones sospechosos en inventario",
    version="1.0.0",
    lifespan=lifespan
)

# Incluir routers
app.include_router(auditoria_router, prefix="/api/auditoria", tags=["Auditoría"])


@app.get("/health")
def health_check(health_service: HealthService = Depends(get_health_service)):
    health_status = health_service.check_overall_health()
    
    if health_status["status"] != "healthy":
        raise HTTPException(status_code=503, detail=health_status)
    
    return health_status

