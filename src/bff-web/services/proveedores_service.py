import httpx
import os
from typing import Optional, Dict, Any
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

    async def crear_proveedor(self, proveedor_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new proveedor via the proveedores service"""
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.base_url}/proveedores/",
                    json=proveedor_data
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
                        detail=f"Error from proveedores service: {response.text}"
                    )
        except httpx.RequestError as e:
            logger.error(f"Error connecting to proveedores service: {str(e)}")
            raise HTTPException(
                status_code=503,
                detail="Proveedores service is not available"
            )
    
    async def listar_proveedores(
        self,
        pais: Optional[str] = None,
        tipo_proveedor: Optional[str] = None,
        page: int = 1,
        page_size: int = 20
    ) -> Dict[str, Any]:
        """List proveedores with optional filters"""
        try:
            params = {
                "page": page,
                "page_size": page_size
            }
            if pais:
                params["pais"] = pais
            if tipo_proveedor:
                params["tipo_proveedor"] = tipo_proveedor
            
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(
                    f"{self.base_url}/proveedores/",
                    params=params
                )
                
                if response.status_code == 200:
                    return response.json()
                else:
                    raise HTTPException(
                        status_code=response.status_code,
                        detail=f"Error from proveedores service: {response.text}"
                    )
        except httpx.RequestError as e:
            logger.error(f"Error connecting to proveedores service: {str(e)}")
            raise HTTPException(
                status_code=503,
                detail="Proveedores service is not available"
            )
    
    async def obtener_proveedor(self, proveedor_id: str) -> Dict[str, Any]:
        """Get a specific proveedor by ID"""
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(
                    f"{self.base_url}/proveedores/{proveedor_id}"
                )
                
                if response.status_code == 200:
                    return response.json()
                elif response.status_code == 404:
                    raise HTTPException(status_code=404, detail="Proveedor no encontrado")
                else:
                    raise HTTPException(
                        status_code=response.status_code,
                        detail=f"Error from proveedores service: {response.text}"
                    )
        except httpx.RequestError as e:
            logger.error(f"Error connecting to proveedores service: {str(e)}")
            raise HTTPException(
                status_code=503,
                detail="Proveedores service is not available"
            )
    
    async def actualizar_proveedor(
        self,
        proveedor_id: str,
        proveedor_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Update an existing proveedor"""
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.put(
                    f"{self.base_url}/proveedores/{proveedor_id}",
                    json=proveedor_data
                )
                
                if response.status_code == 200:
                    return response.json()
                elif response.status_code == 404:
                    raise HTTPException(status_code=404, detail="Proveedor no encontrado")
                elif response.status_code == 409:
                    raise HTTPException(status_code=409, detail=response.json())
                elif response.status_code == 422:
                    raise HTTPException(status_code=422, detail=response.json())
                else:
                    raise HTTPException(
                        status_code=response.status_code,
                        detail=f"Error from proveedores service: {response.text}"
                    )
        except httpx.RequestError as e:
            logger.error(f"Error connecting to proveedores service: {str(e)}")
            raise HTTPException(
                status_code=503,
                detail="Proveedores service is not available"
            )
    
    async def eliminar_proveedor(self, proveedor_id: str) -> Dict[str, Any]:
        """Delete a proveedor"""
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.delete(
                    f"{self.base_url}/proveedores/{proveedor_id}"
                )
                
                if response.status_code == 200:
                    return response.json()
                elif response.status_code == 404:
                    raise HTTPException(status_code=404, detail="Proveedor no encontrado")
                else:
                    raise HTTPException(
                        status_code=response.status_code,
                        detail=f"Error from proveedores service: {response.text}"
                    )
        except httpx.RequestError as e:
            logger.error(f"Error connecting to proveedores service: {str(e)}")
            raise HTTPException(
                status_code=503,
                detail="Proveedores service is not available"
            )


def get_proveedores_service() -> ProveedoresService:
    """Dependency function to get proveedores service instance"""
    return ProveedoresService()


