import httpx
import os
from typing import Dict, Any
from fastapi import HTTPException
import logging

logger = logging.getLogger(__name__)


class VentasService:
    
    def __init__(self):
        self.base_url = os.getenv("VENTAS_SERVICE_URL", "http://ventas-service:3000")
        self.timeout = 30.0
    
    def health_check(self) -> Dict[str, Any]:
        try:
            response = httpx.get(f"{self.base_url}/health", timeout=self.timeout)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            logger.error(f"Health check failed for Ventas microservice: {e}")
            raise HTTPException(status_code=503, detail=f"Ventas service returned error: {e}")
        except httpx.RequestError as e:
            logger.error(f"Failed to connect to Ventas microservice: {e}")
            raise HTTPException(status_code=503, detail=f"Cannot reach Ventas service: {e}")
        except Exception as e:
            logger.error(f"Unexpected error checking Ventas health: {e}")
            raise HTTPException(status_code=500, detail=f"Unexpected error: {e}")

def get_ventas_service() -> VentasService:
    return VentasService()

