import httpx
import os
from typing import Optional, Dict, Any
from fastapi import HTTPException
import logging

logger = logging.getLogger(__name__)


class VendedoresService:
    """Service for communicating with the Ventas microservice (Vendedores endpoints)"""

    def __init__(self):
        self.base_url = os.getenv("VENTAS_SERVICE_URL", "http://ventas-service:3000")
        self.timeout = 30.0

    def health_check(self) -> Dict[str, Any]:
        """Check the health of the Ventas microservice"""
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

    async def crear_vendedor(self, vendedor_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new vendedor via the ventas service"""
        try:
            # Convert Decimal to float for JSON serialization
            if 'meta_venta' in vendedor_data and vendedor_data['meta_venta'] is not None:
                vendedor_data['meta_venta'] = float(vendedor_data['meta_venta'])

            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.base_url}/vendedores/",
                    json=vendedor_data
                )

                if response.status_code == 201:
                    return response.json()
                elif response.status_code == 409:
                    raise HTTPException(status_code=409, detail=response.json())
                elif response.status_code == 422:
                    raise HTTPException(status_code=422, detail=response.json())
                else:
                    raise HTTPException(
                        status_code=response.status_code,
                        detail=f"Error from ventas service: {response.text}"
                    )
        except httpx.RequestError as e:
            logger.error(f"Error connecting to ventas service: {str(e)}")
            raise HTTPException(
                status_code=503,
                detail="Ventas service is not available"
            )

    async def listar_vendedores(
        self,
        page: int = 1,
        page_size: int = 20
    ) -> Dict[str, Any]:
        """List vendedores with pagination"""
        try:
            params = {
                "page": page,
                "page_size": page_size
            }

            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(
                    f"{self.base_url}/vendedores/",
                    params=params
                )

                if response.status_code == 200:
                    return response.json()
                else:
                    raise HTTPException(
                        status_code=response.status_code,
                        detail=f"Error from ventas service: {response.text}"
                    )
        except httpx.RequestError as e:
            logger.error(f"Error connecting to ventas service: {str(e)}")
            raise HTTPException(
                status_code=503,
                detail="Ventas service is not available"
            )

    async def obtener_vendedor(self, vendedor_id: str) -> Dict[str, Any]:
        """Get a specific vendedor by ID"""
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(
                    f"{self.base_url}/vendedores/{vendedor_id}"
                )

                if response.status_code == 200:
                    return response.json()
                elif response.status_code == 404:
                    raise HTTPException(status_code=404, detail="Vendedor no encontrado")
                else:
                    raise HTTPException(
                        status_code=response.status_code,
                        detail=f"Error from ventas service: {response.text}"
                    )
        except httpx.RequestError as e:
            logger.error(f"Error connecting to ventas service: {str(e)}")
            raise HTTPException(
                status_code=503,
                detail="Ventas service is not available"
            )

    async def actualizar_vendedor(
        self,
        vendedor_id: str,
        vendedor_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Update an existing vendedor"""
        try:
            # Convert Decimal to float for JSON serialization
            if 'meta_venta' in vendedor_data and vendedor_data['meta_venta'] is not None:
                vendedor_data['meta_venta'] = float(vendedor_data['meta_venta'])

            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.put(
                    f"{self.base_url}/vendedores/{vendedor_id}",
                    json=vendedor_data
                )

                if response.status_code == 200:
                    return response.json()
                elif response.status_code == 404:
                    raise HTTPException(status_code=404, detail="Vendedor no encontrado")
                elif response.status_code == 409:
                    raise HTTPException(status_code=409, detail=response.json())
                elif response.status_code == 422:
                    raise HTTPException(status_code=422, detail=response.json())
                else:
                    raise HTTPException(
                        status_code=response.status_code,
                        detail=f"Error from ventas service: {response.text}"
                    )
        except httpx.RequestError as e:
            logger.error(f"Error connecting to ventas service: {str(e)}")
            raise HTTPException(
                status_code=503,
                detail="Ventas service is not available"
            )


def get_vendedores_service() -> VendedoresService:
    """Dependency function to get vendedores service instance"""
    return VendedoresService()
