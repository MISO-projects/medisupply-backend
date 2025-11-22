# src/bff-movil/services/visitas_service.py

import httpx
import os
from typing import Dict, Any, Optional, List
from fastapi import HTTPException, UploadFile
import logging
from datetime import date
from pydantic import UUID4 # Usamos UUID4 para tipado
import uuid # Usamos uuid para conversión

# Importamos los schemas del BFF
from schemas.visitas_schema import CrearRutaVisitaSchema

logger = logging.getLogger(__name__)

class VisitasService:
    
    def __init__(self):
        # Asumo que el servicio de visitas corre en el puerto 3000
        # ¡Asegúrate de tener VISITAS_SERVICE_URL en tus variables de entorno!
        self.base_url = os.getenv("VISITAS_SERVICE_URL", "http://visitas-service:3000")
        self.timeout = 30.0

    def health_check(self) -> Dict[str, Any]:
        try:
            response = httpx.get(f"{self.base_url}/health", timeout=self.timeout)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            logger.error(f"Health check failed for Autenticacion microservice: {e}")
            raise HTTPException(status_code=503, detail=f"Autenticacion service returned error: {e}")
        except httpx.RequestError as e:
            logger.error(f"Failed to connect to Autenticacion microservice: {e}")
            raise HTTPException(status_code=503, detail=f"Cannot reach Autenticacion service: {e}")
        except Exception as e:
            logger.error(f"Unexpected error checking Autenticacion health: {e}")
            raise HTTPException(status_code=500, detail=f"Unexpected error: {e}")
    
    
    async def crear_ruta_visita(self, data: CrearRutaVisitaSchema) -> Dict[str, Any]:
        """Llama al endpoint POST /api/visitas/ del microservicio."""
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.base_url}/api/visitas/",
                    json=data.model_dump(mode='json')
                )
                response.raise_for_status()
                return response.json()
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error al crear visita: {e.response.status_code} - {e.response.text}")
            raise HTTPException(status_code=e.response.status_code, detail=e.response.json())
        except httpx.RequestError as e:
            logger.error(f"Failed to connect to Visitas microservice (crear): {e}")
            raise HTTPException(status_code=503, detail="No se puede conectar con el servicio de visitas")
        except Exception as e:
            logger.error(f"Unexpected error al crear visita: {e}")
            raise HTTPException(status_code=500, detail="Error interno del servidor")


    async def get_rutas_del_dia(self, fecha: date, vendedor_id: UUID4, lat_actual, lon_actual) -> List[Dict[str, Any]]:
        """Llama al GET /api/visitas/rutas-del-dia del microservicio."""
        try:
            params = {
                "fecha": str(fecha),
                "vendedor_id": str(vendedor_id),
                "lat_actual": lat_actual,
                "lon_actual": lon_actual
            }
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(
                    f"{self.base_url}/api/visitas/rutas-del-dia",
                    params=params
                )
                response.raise_for_status()
                return response.json()
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error al obtener rutas: {e.response.status_code} - {e.response.text}")
            raise HTTPException(status_code=e.response.status_code, detail=e.response.json())
        except httpx.RequestError as e:
            logger.error(f"Failed to connect to Visitas microservice (rutas): {e}")
            raise HTTPException(status_code=503, detail="No se puede conectar con el servicio de visitas")
        except Exception as e:
            logger.error(f"Unexpected error al obtener rutas: {e}")
            raise HTTPException(status_code=500, detail="Error interno del servidor")


    async def get_visita_detalle(self, visita_id: UUID4, lat_actual, lon_actual) -> Dict[str, Any]:
        """Llama al GET /api/visitas/{visita_id} del microservicio."""
        try:
            params = {
                "lat_actual": lat_actual,
                "lon_actual": lon_actual
            }
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(
                    f"{self.base_url}/api/visitas/{visita_id}",
                    params=params
                )
                response.raise_for_status()
                return response.json()
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error al obtener detalle visita {visita_id}: {e.response.status_code} - {e.response.text}")
            raise HTTPException(status_code=e.response.status_code, detail=e.response.json())
        except httpx.RequestError as e:
            logger.error(f"Failed to connect to Visitas microservice (detalle): {e}")
            raise HTTPException(status_code=503, detail="No se puede conectar con el servicio de visitas")
        except Exception as e:
            logger.error(f"Unexpected error al obtener detalle visita: {e}")
            raise HTTPException(status_code=500, detail="Error interno del servidor")


    async def actualizar_visita(self, 
        visita_id: uuid.UUID, 
        detalle: Optional[str] = None,
        cliente_contacto: Optional[str] = None,
        inicio_str: Optional[str] = None,
        fin_str: Optional[str] = None,
        estado: Optional[str] = None,
        archivo_evidencia: Optional[UploadFile] = None
    ) -> Dict[str, Any]:
        """
        Llama al PUT /api/visitas/{visita_id} del microservicio.
        Reenvía los datos como Multipart/Form-Data.
        """
        try:
            form_data = {}
            if detalle:
                form_data["detalle"] = detalle
            if cliente_contacto:
                form_data["cliente_contacto"] = cliente_contacto
            if inicio_str:
                form_data["inicio"] = inicio_str
            if fin_str:
                form_data["fin"] = fin_str
            if estado:
                form_data["estado"] = estado

            files_payload = None
            if archivo_evidencia:
                file_content = await archivo_evidencia.read()
                files_payload = {
                    "evidencia": (
                        archivo_evidencia.filename, 
                        file_content, 
                        archivo_evidencia.content_type
                    )
                }

            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.put(
                    f"{self.base_url}/api/visitas/{visita_id}",
                    data=form_data,   
                    files=files_payload 
                )
                response.raise_for_status()
                return response.json()
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error al actualizar visita {visita_id}: {e.response.status_code} - {e.response.text}")
            raise HTTPException(status_code=e.response.status_code, detail=e.response.json().get('detail', str(e)))
        except httpx.RequestError as e:
            logger.error(f"Failed to connect to Visitas microservice (actualizar): {e}")
            raise HTTPException(status_code=503, detail="No se puede conectar con el servicio de visitas")
        except Exception as e:
            logger.error(f"Unexpected error al actualizar visita en BFF: {e}")
            raise HTTPException(status_code=500, detail="Error interno en el BFF")


def get_visitas_service() -> VisitasService:
    """Dependency para inyectar el servicio de visitas"""
    return VisitasService()