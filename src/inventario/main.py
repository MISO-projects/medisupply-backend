from fastapi import FastAPI, Depends, HTTPException
from services.health_service import HealthService, get_health_service

app = FastAPI()


@app.get("/health")
def health_check(health_service: HealthService = Depends(get_health_service)):
    health_status = health_service.check_overall_health()
    
    if health_status["status"] != "healthy":
        raise HTTPException(status_code=503, detail=health_status)
    
    return health_status

