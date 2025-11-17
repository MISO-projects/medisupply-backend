from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Optional
import logging

from services.inventario_service import InventarioService, get_inventario_service

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

inventario_router = APIRouter()


@inventario_router.get(
    "/",
    summary="Consultar inventario con filtros",
    description="Retorna una lista paginada de registros de inventario con filtros opcionales"
)
def get_inventario_filtrado(
    text_search: Optional[str] = Query(
        None,
        description="Buscar en nombre de producto, SKU, o ubicación de inventario (búsqueda parcial, case-insensitive)"
    ),
    categoria: Optional[str] = Query(
        None,
        description="Filtrar por categoría de producto"
    ),
    estado: Optional[str] = Query(
        None,
        description="Filtrar por estado de inventario (ej: DISPONIBLE, AGOTADO, RESERVADO)"
    ),
    page: int = Query(1, ge=1, description="Número de página"),
    page_size: int = Query(20, ge=1, le=100, description="Tamaño de página (máximo 100)"),
    inventario_service: InventarioService = Depends(get_inventario_service)
):
    try:
        logger.info(
            f"BFF Móvil: Solicitud de inventario filtrado - "
            f"text_search: {text_search}, categoria: {categoria}, "
            f"estado: {estado}, page: {page}, page_size: {page_size}"
        )
        
        result = inventario_service.get_inventario_filtrado(
            text_search=text_search,
            categoria=categoria,
            estado=estado,
            page=page,
            page_size=page_size
        )
        
        logger.info(f"BFF Móvil: Retornando {result.get('total', 0)} registros de inventario")
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"BFF Móvil: Error interno al procesar solicitud de inventario filtrado: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Error interno del servidor BFF móvil"
        )

