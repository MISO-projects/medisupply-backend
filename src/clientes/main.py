from fastapi import FastAPI, Depends, HTTPException
from services.health_service import HealthService, get_health_service
from router.cliente_router import router as cliente_router
from router.mock_router import router as mock_router

app = FastAPI(
    title="MediSupply Clientes Service",
    description="Servicio para gestión de clientes institucionales",
    version="1.0.0"
)

# Incluir routers
app.include_router(cliente_router)
app.include_router(mock_router)


@app.get("/health")
def health_check(health_service: HealthService = Depends(get_health_service)):
    health_status = health_service.check_overall_health()
    
    if health_status["status"] != "healthy":
        raise HTTPException(status_code=503, detail=health_status)
    
    return health_status

