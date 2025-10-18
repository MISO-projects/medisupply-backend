from fastapi import FastAPI, Depends, HTTPException
from services.health_service import HealthService, get_health_service
from router.auth_router import router as auth_router
from db.database import engine, Base
import logging

logging.basicConfig(level=logging.DEBUG, force=True)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="MediSupply Autenticación Service",
    description="Servicio de autenticación y gestión de usuarios",
    version="1.0.0"
)

Base.metadata.create_all(bind=engine)
logger.info("Database tables created successfully")

# Incluir routers
app.include_router(auth_router)


@app.get("/health")
def health_check(health_service: HealthService = Depends(get_health_service)):
    health_status = health_service.check_overall_health()

    if health_status["status"] != "healthy":
        raise HTTPException(status_code=503, detail=health_status)

    return health_status

