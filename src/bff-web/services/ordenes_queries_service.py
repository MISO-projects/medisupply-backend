import httpx
import os
from typing import Dict, Any
from fastapi import HTTPException
import logging
from typing import Optional

logger = logging.getLogger(__name__)


class OrdenesQueriesService:
    
    def __init__(self):
        self.base_url = os.getenv("ORDENES_QUERIES_SERVICE_URL", "http://order-query-api:3000")
        self.timeout = 30.0
    
    def health_check(self) -> Dict[str, Any]:
        try:
            response = httpx.get(f"{self.base_url}/health", timeout=self.timeout)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            logger.error(f"Health check failed for OrdenesQueries microservice: {e}")
            raise HTTPException(status_code=503, detail=f"OrdenesQueries service returned error: {e}")
        except httpx.RequestError as e:
            logger.error(f"Failed to connect to OrdenesQueries microservice: {e}")
            raise HTTPException(status_code=503, detail=f"Cannot reach OrdenesQueries service: {e}")
        except Exception as e:
            logger.error(f"Unexpected error checking OrdenesQueries health: {e}")
            raise HTTPException(status_code=500, detail=f"Unexpected error: {e}")

    async def list_orders(
        self,
        estado: Optional[str],
        fecha_creacion_desde: Optional[str],
        fecha_creacion_hasta: Optional[str],
        page: int,
        page_size: int
    ) -> Dict[str, Any]:
        try:
            params: Dict[str, Any] = {
                "page": page,
                "page_size": page_size
            }
            if estado:
                params["estado"] = estado
            if fecha_creacion_desde:
                params["fecha_creacion_desde"] = fecha_creacion_desde
            if fecha_creacion_hasta:
                params["fecha_creacion_hasta"] = fecha_creacion_hasta

            async with httpx.AsyncClient(timeout=self.timeout) as client:
                resp = await client.get(f"{self.base_url}/orders/", params=params)
                resp.raise_for_status()
                return resp.json()
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error listing orders: {e.response.status_code} {e.response.text}")
            raise HTTPException(status_code=e.response.status_code, detail="Error del servicio de consultas de órdenes")
        except httpx.RequestError as e:
            logger.error(f"Failed to connect to OrdenesQueries microservice: {e}")
            raise HTTPException(status_code=503, detail="No se puede conectar con el servicio de consultas de órdenes")
        except Exception as e:
            logger.error(f"Unexpected error listing orders: {e}")
            raise HTTPException(status_code=500, detail="Error interno del BFF web al listar órdenes")

def get_ordenes_queries_service() -> OrdenesQueriesService:
    return OrdenesQueriesService()

