from fastapi import APIRouter, Depends, Query, Path
from sqlalchemy.orm import Session
from typing import Optional
import logging
from http import HTTPStatus
from schemas.inventario_schema import CrearRegistroInventarioSchema, RegistroInventarioResponseSchema, StockDisponibleResponse
from typing import List

from services.inventario_service import InventarioService, get_inventario_service
# from schemas.inventario_schema import (
#     # InventarioListResponse, 
#     # InventarioConDetalle
# )

# from db.database import get_db

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

inventario_router = APIRouter()


@inventario_router.get(
    "/",
    # response_model=InventarioListResponse,
    summary="Obtener inventario disponible",
    description="""
    Retorna la lista de productos disponibles con su información de stock.
    
    Criterios: 
    - Solo productos marcados como disponibles
    - Opcionalmente filtrar solo productos con stock > 0
    - Incluye: imagen, nombre, cantidad disponible, categoría, disponibilidad
     PARA WEB: producto(SKU), cantidad, bodega, lote, fecha de vencimiento, condicion de almacenamiento
    """
)
def get_inventario_disponible(
    # solo_con_stock: bool = Query(
    #     True,
    #     description="Si es True, solo retorna productos con stock mayor a 0"
    # ),
    # categoria: Optional[str] = Query(
    #     None,
    #     description="Filtrar por categoría específica"
    # ),
    # nombre: Optional[str] = Query(
    #     None,
    #     description="Buscar productos por nombre (búsqueda parcial, case-insensitive)"
    # ),
    # page: int = Query(1, ge=1, description="Número de página"),
    # page_size: int = Query(20, ge=1, le=100, description="Tamaño de página (máximo 100)"),
    # db: Session = Depends(get_db)
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

        return {"message": "Endpoint de inventario disponible - en construcción"}
        
    except Exception as e:
        logger.error(f"Error en endpoint de inventario disponible: {str(e)}")
        raise

@inventario_router.post(
    "/",
    response_model=RegistroInventarioResponseSchema,
    status_code=HTTPStatus.CREATED
)
def crear_registro(
    data: CrearRegistroInventarioSchema,
    service: InventarioService = Depends(get_inventario_service)
):
    """Crea un nuevo registro de inventario."""
    registro_dict = service.crear_registro_inventario(data)
    return registro_dict

@inventario_router.get(
    "/stock",
    # response_model=List[RegistroInventarioResponseSchema], # O StockDisponibleResponse
    response_model=StockDisponibleResponse,
    status_code=HTTPStatus.OK
)
def listar_stock(
    service: InventarioService = Depends(get_inventario_service)
):
    """
    Obtiene la lista de todos los registros de inventario que tienen stock > 0
    y están disponibles para la venta o reserva.
    """
    stock_disponible = service.listar_stock_disponible()
    
    # return stock_disponible 
    return StockDisponibleResponse(items=stock_disponible, total=len(stock_disponible))