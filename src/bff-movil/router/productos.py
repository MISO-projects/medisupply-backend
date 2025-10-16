from fastapi import APIRouter, Depends, HTTPException, Query, Path
from typing import Optional
import logging

from services.productos_service import ProductosService, get_productos_service

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

productos_router = APIRouter()


@productos_router.get("/health")
def health_check(productos_service: ProductosService = Depends(get_productos_service)):
    return productos_service.health_check()


@productos_router.get(
    "/disponibles",
    summary="Consultar productos con stock disponible",

)
def get_productos_disponibles(
    solo_con_stock: bool = Query(
        True,
        description="Si es True, solo retorna productos con stock mayor a 0"
    ),
    categoria: Optional[str] = Query(
        None,
        description="Filtrar por categoría específica (ej: MEDICAMENTOS, INSUMOS, EQUIPOS)"
    ),
    skip: int = Query(
        0,
        ge=0,
        description="Número de registros a saltar para paginación"
    ),
    limit: int = Query(
        100,
        ge=1,
        le=500,
        description="Cantidad máxima de productos a retornar"
    ),
    productos_service: ProductosService = Depends(get_productos_service)
):

    try:
        logger.info(
            f"BFF Móvil: Solicitud de productos disponibles - "
            f"solo_con_stock: {solo_con_stock}, categoria: {categoria}"
        )
        
        result = productos_service.get_productos_disponibles(
            solo_con_stock=solo_con_stock,
            categoria=categoria,
            skip=skip,
            limit=limit
        )
        
        logger.info(f"BFF Móvil: Retornando {result.get('total', 0)} productos disponibles")
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"BFF Móvil: Error interno al procesar solicitud de productos disponibles: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Error interno del servidor BFF móvil"
        )


@productos_router.get(
    "/{producto_id}",
    summary="Obtener detalle de un producto específico",
    description="Retorna la información completa de un producto por su ID"
)
def get_producto(
    producto_id: str = Path(..., description="ID del producto a consultar"),
    productos_service: ProductosService = Depends(get_productos_service)
):

    try:
        logger.info(f"BFF Móvil: Solicitud de producto {producto_id} recibida")
        
        result = productos_service.get_producto_by_id(producto_id)
        
        logger.info(f"BFF Móvil: Producto {producto_id} encontrado y retornado")
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"BFF Móvil: Error interno al procesar solicitud de producto {producto_id}: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Error interno del servidor BFF móvil"
        )

