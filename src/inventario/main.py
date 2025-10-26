from fastapi import FastAPI, Depends, HTTPException
from services.health_service import HealthService, get_health_service
from router.inventario_router import inventario_router
from db.database import engine, Base
# from models.inventario_schema import Inventario
# from fastapi.middleware.cors import CORSMiddleware
import logging 
import os

logging.basicConfig(level=logging.DEBUG, force=True)
logger = logging.getLogger(__name__)

# Crear las tablas en la base de datos solo si no estamos en modo testing
if not os.getenv("TESTING"):
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables created successfully")

app = FastAPI(
    title="MediSupply - Inventario Service",
    description="Microservicio de gestión de inventario",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# app.add_middleware( 
#     CORSMiddleware,
#     allow_origins=["*"],
#     allow_credentials=True,
#     allow_methods=["*"],
#     allow_headers=["*"],
# )

app.include_router(inventario_router, prefix="/api/inventario", tags=["inventario"])

@app.get("/health")
def health_check(health_service: HealthService = Depends(get_health_service)):
    health_status = health_service.check_overall_health()
    
    if health_status["status"] != "healthy":
        raise HTTPException(status_code=503, detail=health_status)
    
    return health_status

