import httpx
import os
from typing import Dict, Any, List
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

    def get_clientes_asignados(self, authorization_header: str) -> Dict[str, Any]:
        try:
            headers = {
                "Authorization": authorization_header,
                "Content-Type": "application/json"
            }
            
            response = httpx.get(
                f"{self.base_url}/api/clientes/asignados",
                headers=headers,
                timeout=self.timeout
            )
            response.raise_for_status()
            
            logger.info(f"Successfully retrieved clientes asignados from service")
            return response.json()
            
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error getting clientes asignados: {e}")
            if e.response.status_code == 401:
                raise HTTPException(status_code=401, detail="Token de autorización inválido o expirado")
            elif e.response.status_code == 404:
                raise HTTPException(status_code=404, detail="No se encontraron clientes asignados")
            else:
                raise HTTPException(status_code=e.response.status_code, detail=f"Error del servicio de clientes: {e}")
        except httpx.RequestError as e:
            logger.error(f"Failed to connect to Clientes microservice: {e}")
            raise HTTPException(status_code=503, detail="No se puede conectar con el servicio de clientes")
        except Exception as e:
            logger.error(f"Unexpected error getting clientes asignados: {e}")
            raise HTTPException(status_code=500, detail="Error interno del servidor")

    def get_cliente_asignado(self, cliente_id: str, authorization_header: str) -> Dict[str, Any]:
        try:
            headers = {
                "Authorization": authorization_header,
                "Content-Type": "application/json"
            }
            
            response = httpx.get(
                f"{self.base_url}/api/clientes/asignados/{cliente_id}",
                headers=headers,
                timeout=self.timeout
            )
            response.raise_for_status()
            
            logger.info(f"Successfully retrieved cliente {cliente_id} from service")
            return response.json()
            
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error getting cliente {cliente_id}: {e}")
            if e.response.status_code == 401:
                raise HTTPException(status_code=401, detail="Token de autorización inválido o expirado")
            elif e.response.status_code == 404:
                raise HTTPException(status_code=404, detail=f"Cliente {cliente_id} no encontrado o no asignado al vendedor")
            else:
                raise HTTPException(status_code=e.response.status_code, detail=f"Error del servicio de clientes: {e}")
        except httpx.RequestError as e:
            logger.error(f"Failed to connect to Clientes microservice: {e}")
            raise HTTPException(status_code=503, detail="No se puede conectar con el servicio de clientes")
        except Exception as e:
            logger.error(f"Unexpected error getting cliente {cliente_id}: {e}")
            raise HTTPException(status_code=500, detail="Error interno del servidor")
        
    async def get_clientes_by_ids(self, cliente_ids: List[str]) -> List[Dict[str, Any]]:
        """
        Obtiene múltiples clientes por sus IDs en una sola llamada.
        
        Args:
            cliente_ids: Lista de IDs de clientes
            
        Returns:
            Lista de clientes encontrados
        """
        try:
            if not cliente_ids:
                return []
            
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.base_url}/api/clientes/by-ids",
                    json={"ids": cliente_ids}
                )
                
                if response.status_code == 200:
                    return response.json()
                else:
                    logger.warning(f"Error fetching clients by IDs: {response.status_code}")
                    return []
                    
        except httpx.RequestError as e:
            logger.error(f"Failed to connect to Clientes microservice: {e}")
            # Return empty list instead of raising exception to not break order listing
            return []
        except Exception as e:
            logger.error(f"Unexpected error getting clientes by IDs: {e}")
            return []
    
    async def register_client(self, register_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Llama al endpoint de registro del servicio de Clientes.
        Este endpoint es público y no requiere token.

        Args:
            register_data: Datos del nuevo cliente (nombre, nit, etc.).

        Returns:
            Dict con la información del cliente creado.
        """
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}/api/clientes/",
                    json=register_data,
                    timeout=self.timeout
                )
                response.raise_for_status()
                return response.json()
        except httpx.HTTPStatusError as e:
            logger.error(f"Error registering client: {e.response.text}")
            detail = e.response.json().get("detail", "Error en el registro")
            raise HTTPException(status_code=e.response.status_code, detail=detail)
        except httpx.RequestError as e:
            logger.error(f"Failed to connect to Clientes microservice: {e}")
            raise HTTPException(status_code=503, detail="No se puede conectar al servicio de clientes")
        except Exception as e:
            logger.error(f"Unexpected error during client registration: {e}")
            raise HTTPException(status_code=500, detail="Error inesperado durante el registro del cliente")

# Función de dependencia para inyectar el servicio en los endpoints del BFF
def get_clientes_service() -> ClientesService:
    return ClientesService()

