from fastapi import FastAPI, Depends, HTTPException
from services.health_service import HealthService, get_health_service
from router.visita_router import visita_router
from db.database import engine, Base
from db.visita import Visita
import logging 
import os 

logging.basicConfig(level=logging.DEBUG, force=True)
logger = logging.getLogger(__name__)

TESTING = os.getenv("TESTING", "0") == "1"


app = FastAPI(
    title="MediSupply - Visita Service",
    description="Microservicio de gestión de visita",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

if not TESTING:
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables created successfully")
else:
    logger.info("TESTING mode: Skipping table creation")


app.include_router(visita_router, prefix="/api/visitas", tags=["visitas"])

@app.get("/health")
def health_check(health_service: HealthService = Depends(get_health_service)):
    health_status = health_service.check_overall_health()
    
    if health_status["status"] != "healthy":
        raise HTTPException(status_code=503, detail=health_status)
    
    return health_status

