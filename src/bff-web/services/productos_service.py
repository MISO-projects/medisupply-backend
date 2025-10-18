import httpx
import os
from typing import Dict, Any, Optional
from fastapi import HTTPException
import logging

logger = logging.getLogger(__name__)


class ProductosService:
    
    def __init__(self):
        self.base_url = os.getenv("PRODUCTOS_SERVICE_URL", "http://productos-service:3000")
        self.timeout = 30.0
    
    def health_check(self) -> Dict[str, Any]:
        try:
            response = httpx.get(f"{self.base_url}/health", timeout=self.timeout)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            logger.error(f"Health check failed for Productos microservice: {e}")
            raise HTTPException(status_code=503, detail=f"Productos service returned error: {e}")
        except httpx.RequestError as e:
            logger.error(f"Failed to connect to Productos microservice: {e}")
            raise HTTPException(status_code=503, detail=f"Cannot reach Productos service: {e}")
        except Exception as e:
            logger.error(f"Unexpected error checking Productos health: {e}")
            raise HTTPException(status_code=500, detail=f"Unexpected error: {e}")

    
    
    def get_productos_disponibles(
        self,
        solo_con_stock: bool = True,
        categoria: Optional[str] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> Dict[str, Any]:
        """
        Obtiene la lista de productos disponibles con stock
        
        Args:
            solo_con_stock: Si True, solo retorna productos con stock > 0
            categoria: Filtro opcional por categoría
            page: Número de página
            page_size: Tamaño de página
            
        Returns:
            Diccionario con 'total', 'page', 'page_size', 'total_pages' y 'productos'
        """
        try:
            params = {
                "solo_con_stock": solo_con_stock,
                "page": page,
                "page_size": page_size,
            }
            
            if categoria:
                params["categoria"] = categoria
            
            response = httpx.get(
                f"{self.base_url}/api/productos/disponibles",
                params=params,
                timeout=self.timeout
            )
            response.raise_for_status()
            
            logger.info(f"Successfully retrieved productos disponibles from service")
            return response.json()
            
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error getting productos disponibles: {e}")
            if e.response.status_code == 404:
                raise HTTPException(status_code=404, detail="No se encontraron productos disponibles")
            else:
                raise HTTPException(status_code=e.response.status_code, detail=f"Error del servicio de productos: {e}")
        except httpx.RequestError as e:
            logger.error(f"Failed to connect to Productos microservice: {e}")
            raise HTTPException(status_code=503, detail="No se puede conectar con el servicio de productos")
        except Exception as e:
            logger.error(f"Unexpected error getting productos disponibles: {e}")
            raise HTTPException(status_code=500, detail="Error interno del servidor")
    
    def get_producto_by_id(self, producto_id: str) -> Dict[str, Any]:
        """
        Obtiene un producto específico por su ID
        
        Args:
            producto_id: ID del producto a consultar
            
        Returns:
            Diccionario con la información del producto
        """
        try:
            response = httpx.get(
                f"{self.base_url}/api/productos/{producto_id}",
                timeout=self.timeout
            )
            response.raise_for_status()
            
            logger.info(f"Successfully retrieved producto {producto_id} from service")
            return response.json()
            
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error getting producto {producto_id}: {e}")
            if e.response.status_code == 404:
                raise HTTPException(status_code=404, detail=f"Producto {producto_id} no encontrado")
            else:
                raise HTTPException(status_code=e.response.status_code, detail=f"Error del servicio de productos: {e}")
        except httpx.RequestError as e:
            logger.error(f"Failed to connect to Productos microservice: {e}")
            raise HTTPException(status_code=503, detail="No se puede conectar con el servicio de productos")
        except Exception as e:
            logger.error(f"Unexpected error getting producto {producto_id}: {e}")
            raise HTTPException(status_code=500, detail="Error interno del servidor")
    
    async def crear_producto(self, producto_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Crea un nuevo producto en el sistema
        
        Args:
            producto_data: Diccionario con los datos del producto a crear
            
        Returns:
            Diccionario con la información del producto creado
        """
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.base_url}/api/productos/",
                    json=producto_data
                )
                response.raise_for_status()
                
                logger.info(f"Successfully created producto: {producto_data.get('nombre')}")
                return response.json()
                
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error creating producto: {e}")
            error_detail = "Error al crear producto"
            try:
                error_data = e.response.json()
                error_detail = error_data.get("detail", error_detail)
            except:
                pass
            
            if e.response.status_code == 400:
                raise HTTPException(status_code=400, detail=error_detail)
            else:
                raise HTTPException(status_code=e.response.status_code, detail=f"Error del servicio de productos: {error_detail}")
        except httpx.RequestError as e:
            logger.error(f"Failed to connect to Productos microservice: {e}")
            raise HTTPException(status_code=503, detail="No se puede conectar con el servicio de productos")
        except Exception as e:
            logger.error(f"Unexpected error creating producto: {e}")
            raise HTTPException(status_code=500, detail="Error interno del servidor")


def get_productos_service() -> ProductosService:
    return ProductosService()

