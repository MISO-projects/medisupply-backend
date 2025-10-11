import httpx
import os
from typing import Dict, Any
from fastapi import HTTPException
import logging

logger = logging.getLogger(__name__)


class ProveedoresService:
    """Service for communicating with the Proveedores microservice"""
    
    def __init__(self):
        self.base_url = os.getenv("PROVEEDORES_SERVICE_URL", "http://proveedores-service:3000")
        self.timeout = 30.0
    
    def health_check(self) -> Dict[str, Any]:
        """Check the health of the Proveedores microservice"""
        try:
            response = httpx.get(f"{self.base_url}/health", timeout=self.timeout)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            logger.error(f"Health check failed for Proveedores microservice: {e}")
            raise HTTPException(status_code=503, detail=f"Proveedores service returned error: {e}")
        except httpx.RequestError as e:
            logger.error(f"Failed to connect to Proveedores microservice: {e}")
            raise HTTPException(status_code=503, detail=f"Cannot reach Proveedores service: {e}")
        except Exception as e:
            logger.error(f"Unexpected error checking Proveedores health: {e}")
            raise HTTPException(status_code=500, detail=f"Unexpected error: {e}")

def get_proveedores_service() -> ProveedoresService:
    """Dependency function to get proveedores service instance"""
    return ProveedoresService()
