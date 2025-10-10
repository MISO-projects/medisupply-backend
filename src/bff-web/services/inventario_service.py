import httpx
import os
from typing import Dict, Any
from fastapi import HTTPException
import logging

logger = logging.getLogger(__name__)


class InventarioService:
    
    def __init__(self):
        self.base_url = os.getenv("INVENTARIO_SERVICE_URL", "http://inventario-service:3000")
        self.timeout = 30.0
    
    def health_check(self) -> Dict[str, Any]:
        try:
            response = httpx.get(f"{self.base_url}/health", timeout=self.timeout)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            logger.error(f"Health check failed for Inventario microservice: {e}")
            raise HTTPException(status_code=503, detail=f"Inventario service returned error: {e}")
        except httpx.RequestError as e:
            logger.error(f"Failed to connect to Inventario microservice: {e}")
            raise HTTPException(status_code=503, detail=f"Cannot reach Inventario service: {e}")
        except Exception as e:
            logger.error(f"Unexpected error checking Inventario health: {e}")
            raise HTTPException(status_code=500, detail=f"Unexpected error: {e}")

def get_inventario_service() -> InventarioService:
    return InventarioService()

