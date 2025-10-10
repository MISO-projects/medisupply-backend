import httpx
import os
from typing import Dict, Any
from fastapi import HTTPException
import logging

logger = logging.getLogger(__name__)


class ClientesService:
    
    def __init__(self):
        self.base_url = os.getenv("CLIENTES_SERVICE_URL", "http://clientes-service:3000")
        self.timeout = 30.0
    
    def health_check(self) -> Dict[str, Any]:
        try:
            response = httpx.get(f"{self.base_url}/health", timeout=self.timeout)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            logger.error(f"Health check failed for Clientes microservice: {e}")
            raise HTTPException(status_code=503, detail=f"Clientes service returned error: {e}")
        except httpx.RequestError as e:
            logger.error(f"Failed to connect to Clientes microservice: {e}")
            raise HTTPException(status_code=503, detail=f"Cannot reach Clientes service: {e}")
        except Exception as e:
            logger.error(f"Unexpected error checking Clientes health: {e}")
            raise HTTPException(status_code=500, detail=f"Unexpected error: {e}")

def get_clientes_service() -> ClientesService:
    return ClientesService()

