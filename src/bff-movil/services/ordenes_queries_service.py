import httpx
import os
from typing import Dict, Any, Optional
from fastapi import HTTPException
from datetime import datetime
import logging

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
    
    async def listar_ordenes(
        self,
        estado: Optional[str] = None,
        fecha_creacion_desde: Optional[datetime] = None,
        fecha_creacion_hasta: Optional[datetime] = None,
        page: int = 1,
        page_size: int = 20
    ) -> Dict[str, Any]:
        """List orders with optional filters"""
        try:
            params = {
                "page": page,
                "page_size": page_size
            }
            if estado:
                params["estado"] = estado
            if fecha_creacion_desde:
                params["fecha_creacion_desde"] = fecha_creacion_desde.isoformat()
            if fecha_creacion_hasta:
                params["fecha_creacion_hasta"] = fecha_creacion_hasta.isoformat()
            
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(
                    f"{self.base_url}/orders/",
                    params=params
                )
                
                if response.status_code == 200:
                    return response.json()
                else:
                    raise HTTPException(
                        status_code=response.status_code,
                        detail=f"Error from ordenes queries service: {response.text}"
                    )
        except httpx.RequestError as e:
            logger.error(f"Error connecting to ordenes queries service: {str(e)}")
            raise HTTPException(
                status_code=503,
                detail="Ordenes queries service is not available"
            )
    
    async def obtener_orden(self, order_id: str) -> Dict[str, Any]:
        """Get a specific order by ID"""
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(
                    f"{self.base_url}/orders/{order_id}"
                )
                
                if response.status_code == 200:
                    return response.json()
                elif response.status_code == 404:
                    raise HTTPException(status_code=404, detail="Orden no encontrada")
                else:
                    raise HTTPException(
                        status_code=response.status_code,
                        detail=f"Error from ordenes queries service: {response.text}"
                    )
        except httpx.RequestError as e:
            logger.error(f"Error connecting to ordenes queries service: {str(e)}")
            raise HTTPException(
                status_code=503,
                detail="Ordenes queries service is not available"
            )
        


def get_ordenes_queries_service() -> OrdenesQueriesService:
    return OrdenesQueriesService()

