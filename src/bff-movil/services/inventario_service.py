import httpx
import os
from typing import Dict, Any, Optional
from fastapi import HTTPException
import logging

logger = logging.getLogger(__name__)


class InventarioService:
    
    def __init__(self):
        self.base_url = os.getenv("INVENTARIO_SERVICE_URL", "http://inventario-service:3000")
        self.timeout = 30.0
    
    def health_check(self) -> Dict[str, Any]:
        """Verifica el estado del servicio de inventario"""
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

    def get_inventario_filtrado(
        self,
        text_search: Optional[str] = None,
        categoria: Optional[str] = None,
        estado: Optional[str] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> Dict[str, Any]:
        """
        Obtiene la lista de registros de inventario con filtros opcionales.
        
        Args:
            text_search: Buscar en nombre de producto, SKU, o ubicación de inventario
            categoria: Filtro por categoría de producto
            estado: Filtro por estado de inventario
            page: Número de página
            page_size: Tamaño de página
            
        Returns:
            Diccionario con 'total', 'page', 'page_size', 'total_pages' y 'items'
        """
        try:
            params = {
                "page": page,
                "page_size": page_size,
            }
            
            if text_search:
                params["text_search"] = text_search
            if categoria:
                params["categoria"] = categoria
            if estado:
                params["estado"] = estado
            
            response = httpx.get(
                f"{self.base_url}/api/inventario/",
                params=params,
                timeout=self.timeout
            )
            response.raise_for_status()
            
            logger.info(f"Successfully retrieved inventario filtrado from service")
            return response.json()
            
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error getting inventario filtrado: {e}")
            if e.response.status_code == 404:
                raise HTTPException(status_code=404, detail="No se encontraron registros de inventario")
            else:
                raise HTTPException(status_code=e.response.status_code, detail=f"Error del servicio de inventario: {e}")
        except httpx.RequestError as e:
            logger.error(f"Failed to connect to Inventario microservice: {e}")
            raise HTTPException(status_code=503, detail="No se puede conectar con el servicio de inventario")
        except Exception as e:
            logger.error(f"Unexpected error getting inventario filtrado: {e}")
            raise HTTPException(status_code=500, detail="Error interno del servidor")


def get_inventario_service() -> InventarioService:
    """Dependency para inyectar el servicio de inventario"""
    return InventarioService()

