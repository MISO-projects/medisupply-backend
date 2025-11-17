from fastapi import FastAPI, Depends, HTTPException
from services.health_service import HealthService, get_health_service
from router.reporte_vendedores_router import reporte_vendedores_router

app = FastAPI(
    title="MediSupply - Reportes Service",
    description="Microservicio de reportes y analíticas para MediSupply",
    version="1.0.0"
)

# Incluir routers
app.include_router(reporte_vendedores_router, prefix="/reportes", tags=["reportes"])


@app.get("/health")
def health_check(health_service: HealthService = Depends(get_health_service)):
    health_status = health_service.check_overall_health()

    if health_status["status"] != "healthy":
        raise HTTPException(status_code=503, detail=health_status)

    return health_status

