from fastapi import APIRouter, Depends, Query, Path
from sqlalchemy.orm import Session
from typing import Optional
import logging

from db.database import get_db
from services.productos_service import ProductosService
from services.init_service import InitService
from schemas.producto_schema import (
    ProductoResponse,
    ProductoCreate,
    ProductoUpdate,
    ProductosListResponse,
    ProductoConStock
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

productos_router = APIRouter()


@productos_router.get(
    "/disponibles",
    response_model=ProductosListResponse,
    summary="Obtener productos con stock disponible",
    description="""
    Retorna la lista de productos disponibles con su información de stock.
    
    Criterios:
    - Solo productos marcados como disponibles
    - Opcionalmente filtrar solo productos con stock > 0
    - Incluye: imagen, nombre, cantidad disponible, categoría, disponibilidad
    """
)
def get_productos_disponibles(
    solo_con_stock: bool = Query(
        True,
        description="Si es True, solo retorna productos con stock mayor a 0"
    ),
    categoria: Optional[str] = Query(
        None,
        description="Filtrar por categoría específica"
    ),
    nombre: Optional[str] = Query(
        None,
        description="Buscar productos por nombre (búsqueda parcial, case-insensitive)"
    ),
    page: int = Query(1, ge=1, description="Número de página"),
    page_size: int = Query(20, ge=1, le=100, description="Tamaño de página (máximo 100)"),
    db: Session = Depends(get_db)
):
    """
    Endpoint principal para que representantes de ventas consulten productos disponibles.
    
    Retorna productos con:
    - ID del producto
    - Nombre del producto
    - Categoría
    - Imagen del producto
    - Cantidad disponible en inventario
    - Disponibilidad (activo/inactivo)
    - Precio unitario
    - Unidad de medida
    """
    try:
        logger.info(f"Consultando productos disponibles - solo_con_stock: {solo_con_stock}, categoria: {categoria}, nombre: {nombre}")

        skip = (page - 1) * page_size
        
        service = ProductosService(db)
        productos, total = service.get_productos_disponibles(
            solo_con_stock=solo_con_stock,
            categoria=categoria,
            nombre=nombre,
            skip=skip,
            limit=page_size
        )
        
        logger.info(f"Retornando {len(productos)} productos de un total de {total}")
        
        return ProductosListResponse(
            total=total,
            page=page,
            page_size=page_size,
            total_pages=(total + page_size - 1) // page_size if total > 0 else 0,
            productos=productos
        )
        
    except Exception as e:
        logger.error(f"Error en endpoint de productos disponibles: {str(e)}")
        raise


@productos_router.get(
    "/{producto_id}",
    response_model=ProductoResponse,
    summary="Obtener un producto específico",
    description="Retorna la información completa de un producto por su ID"
)
def get_producto(
    producto_id: str = Path(..., description="ID del producto a consultar"),
    db: Session = Depends(get_db)
):
    """Obtiene un producto específico por ID"""
    try:
        logger.info(f"Consultando producto: {producto_id}")
        
        service = ProductosService(db)
        producto = service.get_producto_by_id(producto_id)
        
        return producto
        
    except Exception as e:
        logger.error(f"Error al consultar producto {producto_id}: {str(e)}")
        raise


@productos_router.post(
    "/",
    response_model=ProductoResponse,
    status_code=201,
    summary="Crear un nuevo producto",
    description="Crea un nuevo producto en el sistema"
)
async def crear_producto(
    producto_data: ProductoCreate,
    db: Session = Depends(get_db)
):
    """Crea un nuevo producto"""
    try:
        logger.info(f"Creando nuevo producto: {producto_data.nombre}")
        
        service = ProductosService(db)
        producto = await service.crear_producto(producto_data)
        
        return ProductoResponse.model_validate(producto)
        
    except Exception as e:
        logger.error(f"Error al crear producto: {str(e)}")
        raise


@productos_router.put(
    "/{producto_id}",
    response_model=ProductoResponse,
    summary="Actualizar un producto",
    description="Actualiza la información de un producto existente"
)
def actualizar_producto(
    producto_id: str = Path(..., description="ID del producto a actualizar"),
    producto_data: ProductoUpdate = ...,
    db: Session = Depends(get_db)
):
    """Actualiza un producto existente"""
    try:
        logger.info(f"Actualizando producto: {producto_id}")
        
        service = ProductosService(db)
        producto = service.actualizar_producto(producto_id, producto_data)
        
        return ProductoResponse.model_validate(producto)
        
    except Exception as e:
        logger.error(f"Error al actualizar producto {producto_id}: {str(e)}")
        raise


@productos_router.delete(
    "/{producto_id}",
    status_code=204,
    summary="Eliminar un producto",
    description="Marca un producto como no disponible (soft delete)"
)
def eliminar_producto(
    producto_id: str = Path(..., description="ID del producto a eliminar"),
    db: Session = Depends(get_db)
):
    """Elimina un producto (soft delete)"""
    try:
        logger.info(f"Eliminando producto: {producto_id}")
        
        service = ProductosService(db)
        service.eliminar_producto(producto_id)
        
        return None
        
    except Exception as e:
        logger.error(f"Error al eliminar producto {producto_id}: {str(e)}")
        raise


@productos_router.patch(
    "/{producto_id}/stock",
    response_model=ProductoResponse,
    summary="Actualizar stock de un producto",
    description="Incrementa o decrementa el stock de un producto"
)
def actualizar_stock(
    producto_id: str = Path(..., description="ID del producto"),
    cantidad: int = Query(..., description="Cantidad a sumar o restar (usar negativo para restar)"),
    db: Session = Depends(get_db)
):
    """Actualiza el stock de un producto"""
    try:
        logger.info(f"Actualizando stock del producto {producto_id}: {cantidad:+d}")
        
        service = ProductosService(db)
        producto = service.actualizar_stock(producto_id, cantidad)
        
        return ProductoResponse.model_validate(producto)
        
    except Exception as e:
        logger.error(f"Error al actualizar stock del producto {producto_id}: {str(e)}")
        raise


@productos_router.post(
    "/init/seed",
    status_code=201,
    summary="Inicializar productos de ejemplo",
    description="""
    Crea productos de ejemplo en la base de datos para testing y desarrollo.
    
    - Si ya existen productos, no hace nada (a menos que force=true)
    - Con force=true, elimina todos los productos existentes y crea los de ejemplo
    - Crea 13 productos en 3 categorías: MEDICAMENTOS, INSUMOS, EQUIPOS
    """
)
def inicializar_productos(
    force: bool = Query(
        False,
        description="Si es true, elimina los productos existentes antes de crear los nuevos"
    ),
    db: Session = Depends(get_db)
):
    """
    Inicializa la base de datos con productos de ejemplo.
    
    Este endpoint es útil para:
    - Inicialización rápida en entornos de desarrollo
    - Testing y demos
    - Restaurar datos de ejemplo
    """
    try:
        logger.info(f"Iniciando seed de productos (force={force})")
        
        init_service = InitService(db)
        result = init_service.inicializar_productos(force=force)
        
        logger.info(f"Seed completado: {result['status']}")
        return result
        
    except Exception as e:
        logger.error(f"Error al inicializar productos: {str(e)}")
        raise


@productos_router.delete(
    "/init/clean",
    status_code=200,
    summary="Limpiar todos los productos",
    description="Elimina todos los productos de la base de datos. ⚠️ Usar con precaución."
)
def limpiar_productos(db: Session = Depends(get_db)):
    """
    Elimina todos los productos de la base de datos.
    
    ⚠️ PRECAUCIÓN: Esta operación no se puede deshacer.
    Use este endpoint solo en entornos de desarrollo/testing.
    """
    try:
        logger.warning("⚠️ Limpiando todos los productos de la base de datos")
        
        init_service = InitService(db)
        result = init_service.limpiar_productos()
        
        logger.info(f"Limpieza completada: {result['status']}")
        return result
        
    except Exception as e:
        logger.error(f"Error al limpiar productos: {str(e)}")
        raise

