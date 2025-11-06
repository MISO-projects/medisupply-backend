from fastapi import APIRouter, Depends, HTTPException, Query, Path, UploadFile, File
from typing import Optional
import logging

from services.productos_service import ProductosService, get_productos_service
from schemas.producto_schema import CrearProductoSchema

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

productos_router = APIRouter()

@productos_router.get("/health")
def health_check(productos_service: ProductosService = Depends(get_productos_service)):
    return productos_service.health_check()

@productos_router.post(
    "/",
    status_code=201,
    summary="Crear un nuevo producto",
    description="Crea un nuevo producto en el sistema"
)
async def crear_producto(
    producto: CrearProductoSchema,
    productos_service: ProductosService = Depends(get_productos_service)
):
    """
    Crea un nuevo producto en el sistema.
    
    Requiere:
    - **nombre**: Nombre del producto (obligatorio, máximo 255 caracteres)
    - **descripcion**: Descripción del producto (opcional)
    - **categoria**: Categoría del producto (obligatorio, máximo 100 caracteres)
    - **imagen_url**: URL de la imagen del producto (opcional, máximo 500 caracteres)
    - **precio_unitario**: Precio unitario del producto (obligatorio, debe ser mayor a 0)
    - **stock_disponible**: Cantidad disponible en stock (obligatorio, debe ser >= 0)
    - **disponible**: Indica si el producto está disponible para venta (obligatorio)
    - **unidad_medida**: Unidad de medida (obligatorio, ej: UNIDAD, CAJA, LITRO)
    - **sku**: SKU del producto (opcional, máximo 100 caracteres)
    - **tipo_almacenamiento**: Tipo de almacenamiento (obligatorio, ej: AMBIENTE, REFRIGERADO, CONGELADO)
    - **observaciones**: Observaciones adicionales del producto (opcional)
    - **proveedor_id**: ID del proveedor (obligatorio, UUID)
    """
    try:
        logger.info(f"BFF Web: Solicitud de creación de producto - nombre: {producto.nombre}")
        
        result = await productos_service.crear_producto(producto.model_dump(mode='json'))
        
        logger.info(f"BFF Web: Producto creado exitosamente - ID: {result.get('id')}")
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"BFF Web: Error interno al procesar solicitud de creación de producto: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Error interno del servidor BFF web"
        )



@productos_router.get(
    "/disponibles",
    summary="Consultar productos creados",

)
def get_productos_creados(
    page: int = Query(1, ge=1, description="Número de página"),
    page_size: int = Query(20, ge=1, le=100, description="Tamaño de página (máximo 100)"),
    productos_service: ProductosService = Depends(get_productos_service)
):
    try:
        logger.info(f"BFF Móvil: Solicitud de productos creados recibida")
        result = productos_service.get_productos_creados(
            page=page,
            page_size=page_size
        )
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
        logger.info(f"BFF Web: Solicitud de producto {producto_id} recibida")
        
        result = productos_service.get_producto_by_id(producto_id)
        
        logger.info(f"BFF Web: Producto {producto_id} encontrado y retornado")
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"BFF Web: Error interno al procesar solicitud de producto {producto_id}: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Error interno del servidor BFF web"
        )


@productos_router.post(
    "/bulk-upload",
    status_code=201,
    summary="Carga masiva de productos desde Excel",
    description="""
    Permite cargar múltiples productos desde un archivo Excel (.xlsx).
    
    El archivo debe contener las siguientes columnas:
    - **nombre** (requerido)
    - **categoria** (requerido)
    - **precio_unitario** (requerido)
    - **proveedor_id** (requerido, UUID)
    - descripcion (opcional)
    - imagen_url (opcional)
    - disponible (opcional, default: true)
    - unidad_medida (opcional, default: UNIDAD)
    - sku (opcional, se genera automáticamente)
    - tipo_almacenamiento (opcional, default: AMBIENTE)
    - observaciones (opcional)
    
    Retorna un resumen detallado con productos creados, actualizados y errores.
    """
)
async def bulk_upload_productos(
    file: UploadFile = File(..., description="Archivo Excel con productos"),
    productos_service: ProductosService = Depends(get_productos_service)
):
    """
    Carga masiva de productos desde archivo Excel.
    
    Si un producto ya existe (mismo nombre y proveedor), se actualiza.
    Si es nuevo, se crea.
    """
    try:
        if not file.filename.endswith(('.xlsx', '.xls')):
            raise HTTPException(
                status_code=400,
                detail="El archivo debe ser un Excel (.xlsx o .xls)"
            )
        
        logger.info(f"BFF Web: Iniciando carga masiva desde archivo: {file.filename}")
        
        result = await productos_service.bulk_upload_productos(file)
        
        logger.info(f"BFF Web: Carga masiva completada - {result.get('successful', 0)} exitosos, {result.get('failed', 0)} fallidos")
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"BFF Web: Error interno al procesar carga masiva: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Error interno del servidor BFF web"
        )

