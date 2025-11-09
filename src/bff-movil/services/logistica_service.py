import httpx
import os
from typing import Dict, Any, Optional
from fastapi import HTTPException
import logging

logger = logging.getLogger(__name__)


class LogisticaService:
    
    def __init__(self):
        self.base_url = os.getenv("LOGISTICA_SERVICE_URL", "http://logistica:3000")
        self.timeout = 30.0
    
    async def obtener_entregas_programadas_cliente(
        self,
        id_cliente: str,
        estado_parada: Optional[str] = None,
        estado_ruta: Optional[str] = None,
        page: int = 1,
        page_size: int = 20
    ) -> Dict[str, Any]:
        """Obtiene las entregas programadas (con ruta asignada) de un cliente"""
        try:
            params = {
                "page": page,
                "page_size": page_size
            }
            
            if estado_parada:
                params["estado_parada"] = estado_parada
            if estado_ruta:
                params["estado_ruta"] = estado_ruta
            
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(
                    f"{self.base_url}/api/rutas/paradas/cliente/{id_cliente}",
                    params=params
                )
                
                if response.status_code == 200:
                    return response.json()
                elif response.status_code == 404:
                    # Si no hay entregas, devolver estructura vacía
                    return {
                        "data": [],
                        "total": 0,
                        "page": page,
                        "page_size": page_size,
                        "total_pages": 0
                    }
                else:
                    raise HTTPException(
                        status_code=response.status_code,
                        detail=f"Error from logistica service: {response.text}"
                    )
        except httpx.RequestError as e:
            logger.error(f"Error connecting to logistica service: {str(e)}")
            raise HTTPException(
                status_code=503,
                detail="Logistica service is not available"
            )


def get_logistica_service() -> LogisticaService:
    return LogisticaService()

