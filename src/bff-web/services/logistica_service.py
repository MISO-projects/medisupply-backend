import httpx
import os
from typing import Dict, Any, List
from fastapi import HTTPException
import logging

logger = logging.getLogger(__name__)


class LogisticaService:
    
    def __init__(self):
        self.base_url = os.getenv("LOGISTICA_SERVICE_URL", "http://logistica-service:3000")
        self.timeout = 30.0
    
    def health_check(self) -> Dict[str, Any]:
        try:
            response = httpx.get(f"{self.base_url}/health", timeout=self.timeout)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            logger.error(f"Health check failed for Logistica microservice: {e}")
            raise HTTPException(status_code=503, detail=f"Logistica service returned error: {e}")
        except httpx.RequestError as e:
            logger.error(f"Failed to connect to Logistica microservice: {e}")
            raise HTTPException(status_code=503, detail=f"Cannot reach Logistica service: {e}")
        except Exception as e:
            logger.error(f"Unexpected error checking Logistica health: {e}")
            raise HTTPException(status_code=500, detail=f"Unexpected error: {e}")

    def crear_ruta(self, ruta_data: Dict[str, Any]) -> Dict[str, Any]:
        try:
            response = httpx.post(
                f"{self.base_url}/api/rutas/",
                json=ruta_data,
                timeout=self.timeout
            )
            response.raise_for_status()

            logger.info(f"Ruta creada exitosamente: {response.json()}")
            return response.json()

        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error creating ruta: {e}")
            error_detail = e.response.text

            if e.response.status_code == 400:
                raise HTTPException(status_code=400, detail=f"Datos inválidos: {error_detail}")
            elif e.response.status_code == 422:
                raise HTTPException(status_code=422, detail=f"Error de validación: {error_detail}")
            else:
                raise HTTPException(
                    status_code=e.response.status_code,
                    detail=f"Error del servicio de logística: {error_detail}"
                )
        except httpx.RequestError as e:
            logger.error(f"Failed to connect to Logistica microservice: {e}")
            raise HTTPException(status_code=503, detail="No se pudo conectar con el servicio de logística")
        except Exception as e:
            logger.error(f"Unexpected error creating ruta: {e}")
            raise HTTPException(status_code=500, detail=f"Error inesperado: {str(e)}")

    def obtener_ruta(self, ruta_id: int) -> Dict[str, Any]:
        try:
            response = httpx.get(
                f"{self.base_url}/api/rutas/{ruta_id}",
                timeout=self.timeout
            )
            response.raise_for_status()

            logger.info(f"Ruta {ruta_id} obtenida exitosamente")
            return response.json()

        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error getting ruta {ruta_id}: {e}")

            if e.response.status_code == 404:
                raise HTTPException(status_code=404, detail=f"Ruta {ruta_id} no encontrada")
            else:
                raise HTTPException(
                    status_code=e.response.status_code,
                    detail=f"Error del servicio de logística: {e.response.text}"
                )
        except httpx.RequestError as e:
            logger.error(f"Failed to connect to Logistica microservice: {e}")
            raise HTTPException(status_code=503, detail="No se pudo conectar con el servicio de logística")
        except Exception as e:
            logger.error(f"Unexpected error getting ruta: {e}")
            raise HTTPException(status_code=500, detail=f"Error inesperado: {str(e)}")

    def listar_rutas(self, page: int = 1, page_size: int = 20) -> Dict[str, Any]:
        try:
            response = httpx.get(
                f"{self.base_url}/api/rutas/",
                params={"page": page, "page_size": page_size},
                timeout=self.timeout
            )
            response.raise_for_status()

            logger.info(f"Listado de rutas obtenido exitosamente (page={page}, page_size={page_size})")
            return response.json()

        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error listing rutas: {e}")
            raise HTTPException(
                status_code=e.response.status_code,
                detail=f"Error del servicio de logística: {e.response.text}"
            )
        except httpx.RequestError as e:
            logger.error(f"Failed to connect to Logistica microservice: {e}")
            raise HTTPException(status_code=503, detail="No se pudo conectar con el servicio de logística")
        except Exception as e:
            logger.error(f"Unexpected error listing rutas: {e}")
            raise HTTPException(status_code=500, detail=f"Error inesperado: {str(e)}")


    def crear_conductor(self, conductor_data: Dict[str, Any]) -> Dict[str, Any]:
        try:
            response = httpx.post(
                f"{self.base_url}/api/conductores/",
                json=conductor_data,
                timeout=self.timeout
            )
            response.raise_for_status()
            logger.info(f"Conductor creado exitosamente")
            return response.json()
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error creating conductor: {e}")
            raise HTTPException(status_code=e.response.status_code, detail=e.response.text)
        except httpx.RequestError as e:
            logger.error(f"Failed to connect to Logistica microservice: {e}")
            raise HTTPException(status_code=503, detail="No se pudo conectar con el servicio de logística")
        except Exception as e:
            logger.error(f"Unexpected error creating conductor: {e}")
            raise HTTPException(status_code=500, detail=f"Error inesperado: {str(e)}")

    def obtener_conductor(self, conductor_id: int) -> Dict[str, Any]:
        try:
            response = httpx.get(
                f"{self.base_url}/api/conductores/{conductor_id}",
                timeout=self.timeout
            )
            response.raise_for_status()
            logger.info(f"Conductor {conductor_id} obtenido exitosamente")
            return response.json()
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error getting conductor {conductor_id}: {e}")
            if e.response.status_code == 404:
                raise HTTPException(status_code=404, detail=f"Conductor {conductor_id} no encontrado")
            raise HTTPException(status_code=e.response.status_code, detail=e.response.text)
        except httpx.RequestError as e:
            logger.error(f"Failed to connect to Logistica microservice: {e}")
            raise HTTPException(status_code=503, detail="No se pudo conectar con el servicio de logística")
        except Exception as e:
            logger.error(f"Unexpected error getting conductor: {e}")
            raise HTTPException(status_code=500, detail=f"Error inesperado: {str(e)}")

    def listar_conductores(self, page: int = 1, page_size: int = 20, activo: bool = None) -> Dict[str, Any]:
        try:
            params = {"page": page, "page_size": page_size}
            if activo is not None:
                params["activo"] = activo
            
            response = httpx.get(
                f"{self.base_url}/api/conductores/",
                params=params,
                timeout=self.timeout
            )
            response.raise_for_status()
            logger.info(f"Listado de conductores obtenido exitosamente")
            return response.json()
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error listing conductores: {e}")
            raise HTTPException(status_code=e.response.status_code, detail=e.response.text)
        except httpx.RequestError as e:
            logger.error(f"Failed to connect to Logistica microservice: {e}")
            raise HTTPException(status_code=503, detail="No se pudo conectar con el servicio de logística")
        except Exception as e:
            logger.error(f"Unexpected error listing conductores: {e}")
            raise HTTPException(status_code=500, detail=f"Error inesperado: {str(e)}")

    def actualizar_conductor(self, conductor_id: int, conductor_data: Dict[str, Any]) -> Dict[str, Any]:
        try:
            response = httpx.put(
                f"{self.base_url}/api/conductores/{conductor_id}",
                json=conductor_data,
                timeout=self.timeout
            )
            response.raise_for_status()
            logger.info(f"Conductor {conductor_id} actualizado exitosamente")
            return response.json()
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error updating conductor {conductor_id}: {e}")
            raise HTTPException(status_code=e.response.status_code, detail=e.response.text)
        except httpx.RequestError as e:
            logger.error(f"Failed to connect to Logistica microservice: {e}")
            raise HTTPException(status_code=503, detail="No se pudo conectar con el servicio de logística")
        except Exception as e:
            logger.error(f"Unexpected error updating conductor: {e}")
            raise HTTPException(status_code=500, detail=f"Error inesperado: {str(e)}")

    def eliminar_conductor(self, conductor_id: int) -> Dict[str, Any]:
        try:
            response = httpx.delete(
                f"{self.base_url}/api/conductores/{conductor_id}",
                timeout=self.timeout
            )
            response.raise_for_status()
            logger.info(f"Conductor {conductor_id} eliminado exitosamente")
            return response.json()
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error deleting conductor {conductor_id}: {e}")
            raise HTTPException(status_code=e.response.status_code, detail=e.response.text)
        except httpx.RequestError as e:
            logger.error(f"Failed to connect to Logistica microservice: {e}")
            raise HTTPException(status_code=503, detail="No se pudo conectar con el servicio de logística")
        except Exception as e:
            logger.error(f"Unexpected error deleting conductor: {e}")
            raise HTTPException(status_code=500, detail=f"Error inesperado: {str(e)}")

    # ========== VEHÍCULOS ==========

    def crear_vehiculo(self, vehiculo_data: Dict[str, Any]) -> Dict[str, Any]:
        try:
            response = httpx.post(
                f"{self.base_url}/api/vehiculos/",
                json=vehiculo_data,
                timeout=self.timeout
            )
            response.raise_for_status()
            logger.info(f"Vehículo creado exitosamente")
            return response.json()
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error creating vehiculo: {e}")
            raise HTTPException(status_code=e.response.status_code, detail=e.response.text)
        except httpx.RequestError as e:
            logger.error(f"Failed to connect to Logistica microservice: {e}")
            raise HTTPException(status_code=503, detail="No se pudo conectar con el servicio de logística")
        except Exception as e:
            logger.error(f"Unexpected error creating vehiculo: {e}")
            raise HTTPException(status_code=500, detail=f"Error inesperado: {str(e)}")

    def obtener_vehiculo(self, vehiculo_id: int) -> Dict[str, Any]:
        try:
            response = httpx.get(
                f"{self.base_url}/api/vehiculos/{vehiculo_id}",
                timeout=self.timeout
            )
            response.raise_for_status()
            logger.info(f"Vehículo {vehiculo_id} obtenido exitosamente")
            return response.json()
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error getting vehiculo {vehiculo_id}: {e}")
            if e.response.status_code == 404:
                raise HTTPException(status_code=404, detail=f"Vehículo {vehiculo_id} no encontrado")
            raise HTTPException(status_code=e.response.status_code, detail=e.response.text)
        except httpx.RequestError as e:
            logger.error(f"Failed to connect to Logistica microservice: {e}")
            raise HTTPException(status_code=503, detail="No se pudo conectar con el servicio de logística")
        except Exception as e:
            logger.error(f"Unexpected error getting vehiculo: {e}")
            raise HTTPException(status_code=500, detail=f"Error inesperado: {str(e)}")

    def listar_vehiculos(self, page: int = 1, page_size: int = 20, activo: bool = None) -> Dict[str, Any]:
        try:
            params = {"page": page, "page_size": page_size}
            if activo is not None:
                params["activo"] = activo
            
            response = httpx.get(
                f"{self.base_url}/api/vehiculos/",
                params=params,
                timeout=self.timeout
            )
            response.raise_for_status()
            logger.info(f"Listado de vehículos obtenido exitosamente")
            return response.json()
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error listing vehiculos: {e}")
            raise HTTPException(status_code=e.response.status_code, detail=e.response.text)
        except httpx.RequestError as e:
            logger.error(f"Failed to connect to Logistica microservice: {e}")
            raise HTTPException(status_code=503, detail="No se pudo conectar con el servicio de logística")
        except Exception as e:
            logger.error(f"Unexpected error listing vehiculos: {e}")
            raise HTTPException(status_code=500, detail=f"Error inesperado: {str(e)}")

    def actualizar_vehiculo(self, vehiculo_id: int, vehiculo_data: Dict[str, Any]) -> Dict[str, Any]:
        try:
            response = httpx.put(
                f"{self.base_url}/api/vehiculos/{vehiculo_id}",
                json=vehiculo_data,
                timeout=self.timeout
            )
            response.raise_for_status()
            logger.info(f"Vehículo {vehiculo_id} actualizado exitosamente")
            return response.json()
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error updating vehiculo {vehiculo_id}: {e}")
            raise HTTPException(status_code=e.response.status_code, detail=e.response.text)
        except httpx.RequestError as e:
            logger.error(f"Failed to connect to Logistica microservice: {e}")
            raise HTTPException(status_code=503, detail="No se pudo conectar con el servicio de logística")
        except Exception as e:
            logger.error(f"Unexpected error updating vehiculo: {e}")
            raise HTTPException(status_code=500, detail=f"Error inesperado: {str(e)}")

    def eliminar_vehiculo(self, vehiculo_id: int) -> Dict[str, Any]:
        try:
            response = httpx.delete(
                f"{self.base_url}/api/vehiculos/{vehiculo_id}",
                timeout=self.timeout
            )
            response.raise_for_status()
            logger.info(f"Vehículo {vehiculo_id} eliminado exitosamente")
            return response.json()
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error deleting vehiculo {vehiculo_id}: {e}")
            raise HTTPException(status_code=e.response.status_code, detail=e.response.text)
        except httpx.RequestError as e:
            logger.error(f"Failed to connect to Logistica microservice: {e}")
            raise HTTPException(status_code=503, detail="No se pudo conectar con el servicio de logística")
        except Exception as e:
            logger.error(f"Unexpected error deleting vehiculo: {e}")
            raise HTTPException(status_code=500, detail=f"Error inesperado: {str(e)}")


def get_logistica_service() -> LogisticaService:
    return LogisticaService()

