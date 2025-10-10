import httpx
import os
from typing import Dict, Any
from fastapi import HTTPException
import logging

logger = logging.getLogger(__name__)


class AutenticacionService:
    
    def __init__(self):
        self.base_url = os.getenv("AUTENTICACION_SERVICE_URL", "http://autenticacion-service:3000")
        self.timeout = 30.0
    
    def health_check(self) -> Dict[str, Any]:
        try:
            response = httpx.get(f"{self.base_url}/health", timeout=self.timeout)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            logger.error(f"Health check failed for Autenticacion microservice: {e}")
            raise HTTPException(status_code=503, detail=f"Autenticacion service returned error: {e}")
        except httpx.RequestError as e:
            logger.error(f"Failed to connect to Autenticacion microservice: {e}")
            raise HTTPException(status_code=503, detail=f"Cannot reach Autenticacion service: {e}")
        except Exception as e:
            logger.error(f"Unexpected error checking Autenticacion health: {e}")
            raise HTTPException(status_code=500, detail=f"Unexpected error: {e}")

def get_autenticacion_service() -> AutenticacionService:
    return AutenticacionService()

