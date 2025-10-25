import httpx
import os
from typing import Dict, Any
from fastapi import HTTPException
import logging

logger = logging.getLogger(__name__)


class OrdenesCommandsService:
    
    def __init__(self):
        self.base_url = os.getenv("ORDENES_COMMANDS_SERVICE_URL", "http://order-command-api:3000")
        self.timeout = 30.0
    
    def health_check(self) -> Dict[str, Any]:
        try:
            response = httpx.get(f"{self.base_url}/health", timeout=self.timeout)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            logger.error(f"Health check failed for OrdenesCommands microservice: {e}")
            raise HTTPException(status_code=503, detail=f"OrdenesCommands service returned error: {e}")
        except httpx.RequestError as e:
            logger.error(f"Failed to connect to OrdenesCommands microservice: {e}")
            raise HTTPException(status_code=503, detail=f"Cannot reach OrdenesCommands service: {e}")
        except Exception as e:
            logger.error(f"Unexpected error checking OrdenesCommands health: {e}")
            raise HTTPException(status_code=500, detail=f"Unexpected error: {e}")
    
    async def create_order(self, order_data: Dict[str, Any], authorization: str) -> Dict[str, Any]:
        """
        Crea una nueva orden en el servicio de comandos de órdenes
        
        Args:
            order_data: Datos de la orden a crear
            authorization: Token de autorización JWT (formato: "Bearer <token>")
            
        Returns:
            Dict con id y numero_orden de la orden creada
            
        Raises:
            HTTPException: Si hay error al crear la orden
        """
        try:
            logger.info(f"Creando orden en OrdenesCommands service")
            
            # Llamar al servicio de comandos de órdenes con el token de autorización
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}/ordenes/",
                    json=order_data,
                    headers={"Authorization": authorization},
                    timeout=self.timeout
                )
                response.raise_for_status()
                
                result = response.json()
                logger.info(f"Orden creada exitosamente: {result.get('numero_orden')}")
                return result
                
        except httpx.HTTPStatusError as e:
            logger.error(f"Error al crear orden - Status {e.response.status_code}: {e.response.text}")
            
            # Intentar extraer el detalle del error de la respuesta
            try:
                error_detail = e.response.json().get("detail", "Error al crear la orden")
            except:
                error_detail = f"Error al crear la orden: {e.response.text}"
            
            raise HTTPException(
                status_code=e.response.status_code,
                detail=error_detail
            )
        except httpx.RequestError as e:
            logger.error(f"Error de conexión con OrdenesCommands microservice: {e}")
            raise HTTPException(
                status_code=503,
                detail=f"No se puede conectar al servicio de órdenes: {str(e)}"
            )
        except Exception as e:
            logger.error(f"Error inesperado al crear orden: {e}")
            raise HTTPException(
                status_code=500,
                detail=f"Error inesperado al crear la orden: {str(e)}"
            )

def get_ordenes_commands_service() -> OrdenesCommandsService:
    return OrdenesCommandsService()

