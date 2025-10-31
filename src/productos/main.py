from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from services.health_service import HealthService, get_health_service
from router.productos_router import productos_router
import logging
import os

logging.basicConfig(level=logging.DEBUG, force=True)
logger = logging.getLogger(__name__)

if not os.getenv("TESTING"):
    from db.database import Base, engine
    Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="MediSupply - Productos Service",
    description="Microservicio de gestión de productos y stock",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(productos_router, prefix="/api/productos", tags=["productos"])


@app.get("/health")
def health_check(health_service: HealthService = Depends(get_health_service)):
    health_status = health_service.check_overall_health()
    
    if health_status["status"] != "healthy":
        raise HTTPException(status_code=503, detail=health_status)
    
    return health_status

