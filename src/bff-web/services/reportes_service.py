import httpx
import os
from typing import Dict, Any, Optional
from fastapi import HTTPException
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class ReportesService:

    def __init__(self):
        self.base_url = os.getenv("REPORTES_SERVICE_URL", "http://reportes-service:3000")
        self.timeout = 30.0

    def health_check(self) -> Dict[str, Any]:
        try:
            response = httpx.get(f"{self.base_url}/health", timeout=self.timeout)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            logger.error(f"Health check failed for Reportes microservice: {e}")
            raise HTTPException(status_code=503, detail=f"Reportes service returned error: {e}")
        except httpx.RequestError as e:
            logger.error(f"Failed to connect to Reportes microservice: {e}")
            raise HTTPException(status_code=503, detail=f"Cannot reach Reportes service: {e}")
        except Exception as e:
            logger.error(f"Unexpected error checking Reportes health: {e}")
            raise HTTPException(status_code=500, detail=f"Unexpected error: {e}")

    async def generar_reporte_vendedores(
        self,
        fecha_inicio: datetime,
        fecha_fin: datetime,
        zona_asignada: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Genera un reporte de vendedores con métricas de ventas.

        Args:
            fecha_inicio: Fecha de inicio del periodo
            fecha_fin: Fecha de fin del periodo
            zona_asignada: Filtro opcional por zona

        Returns:
            Diccionario con el reporte de vendedores
        """
        try:
            params: Dict[str, Any] = {
                "fecha_inicio": fecha_inicio.isoformat(),
                "fecha_fin": fecha_fin.isoformat()
            }

            if zona_asignada:
                params["zona_asignada"] = zona_asignada

            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(
                    f"{self.base_url}/reportes/vendedores",
                    params=params
                )

                if response.status_code == 200:
                    return response.json()
                elif response.status_code == 400:
                    raise HTTPException(status_code=400, detail=response.json().get("detail", "Error en los parámetros"))
                else:
                    raise HTTPException(
                        status_code=response.status_code,
                        detail=f"Error from reportes service: {response.text}"
                    )
        except httpx.RequestError as e:
            logger.error(f"Error connecting to reportes service: {str(e)}")
            raise HTTPException(
                status_code=503,
                detail="Reportes service is not available"
            )
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Unexpected error generating report: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail=f"Unexpected error: {str(e)}"
            )


def get_reportes_service() -> ReportesService:
    return ReportesService()

