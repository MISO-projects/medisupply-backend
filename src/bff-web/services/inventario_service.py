# src/bff-web/services/inventario_service.py

import httpx
import os
from typing import Dict, Any, List
from fastapi import HTTPException
import logging

logger = logging.getLogger(__name__)
 

class InventarioService:
    
    def __init__(self):
        self.base_url = os.getenv("INVENTARIO_SERVICE_URL", "http://inventario-service:3000")
        self.timeout = 30.0
    
    def health_check(self) -> Dict[str, Any]:
        # ... (tu health_check se mantiene) ...
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

    async def crear_registro_inventario(self, data: Dict[str, Any], token: str) -> Dict[str, Any]: # ¡MODIFICADO! Acepta token
        """
        Llama al microservicio de inventario para crear un nuevo registro.
        Propaga el token de autenticación.
        """
        # Prepara el header de autenticación
        auth_header = {"Authorization": token}
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.base_url}/api/inventario/",
                    json=data,
                    headers=auth_header # ¡Añade el header!
                )
                response.raise_for_status()
                return response.json()
        except httpx.HTTPStatusError as e:
            logger.error(f"Error creating inventario record: {e.response.text}")
            detail = e.response.json() if e.response.content else f"Inventario service returned error: {e.response.status_code}"
            raise HTTPException(status_code=e.response.status_code, detail=detail)
        except httpx.RequestError as e:
            logger.error(f"Failed to connect to Inventario microservice: {e}")
            raise HTTPException(status_code=503, detail="Cannot reach Inventario service")
        except Exception as e:
            logger.error(f"Unexpected error creating inventario record: {e}")
            raise HTTPException(status_code=500, detail=f"Unexpected error: {e}")
    
    async def listar_registros_inventario(self, page: int, page_size: int, token: str) -> Dict[str, Any]:
        """
        Llama al microservicio de inventario para obtener la lista paginada
        de registros de inventario.
        """
        # Prepara los headers y parámetros
        auth_header = {"Authorization": token}
        params = {"page": page, "page_size": page_size}
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(
                    f"{self.base_url}/api/inventario/",
                    params=params,
                    headers=auth_header
                )
                response.raise_for_status()
                return response.json()
        
        except httpx.HTTPStatusError as e:
            logger.error(f"Error listing inventario records: {e.response.text}")
            detail = e.response.json() if e.response.content else f"Inventario service returned error: {e.response.status_code}"
            raise HTTPException(status_code=e.response.status_code, detail=detail)
        
        except httpx.RequestError as e:
            logger.error(f"Failed to connect to Inventario microservice: {e}")
            raise HTTPException(status_code=503, detail="Cannot reach Inventario service")
        
        except Exception as e:
            logger.error(f"Unexpected error listing inventario records: {e}")
            raise HTTPException(status_code=500, detail=f"Unexpected error: {e}")

def get_inventario_service() -> InventarioService:
    return InventarioService()