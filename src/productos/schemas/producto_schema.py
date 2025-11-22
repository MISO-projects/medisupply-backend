from pydantic import BaseModel, Field
from typing import Optional, List, Dict
from datetime import datetime
from decimal import Decimal
from uuid import UUID

class ProductoBase(BaseModel):
    nombre: str = Field(..., min_length=1, max_length=255)
    descripcion: Optional[str] = None
    categoria: str = Field(..., min_length=1, max_length=100)
    imagen_url: Optional[str] = None
    precio_unitario: Decimal
    stock_disponible: int = Field(default=0, ge=0)
    disponible: bool = True
    unidad_medida: str = Field("UNIDAD", max_length=50)
    sku: Optional[str] = None
    tipo_almacenamiento: str = Field("AMBIENTE", max_length=50)
    observaciones: Optional[str] = None
    proveedor_id: UUID


class ProductoCreate(ProductoBase):
    pass 


class ProductoUpdate(BaseModel):
    nombre: Optional[str] = None
    descripcion: Optional[str] = None
    categoria: Optional[str] = None
    imagen_url: Optional[str] = None
    precio_unitario: Optional[Decimal] = None
    stock_disponible: Optional[int] = Field(None, ge=0)
    disponible: Optional[bool] = None
    unidad_medida: Optional[str] = None
    sku: Optional[str] = None
    tipo_almacenamiento: Optional[str] = None
    observaciones: Optional[str] = None
    proveedor_id: Optional[UUID] = None
class ProductoResponse(ProductoBase):
    id: str
    proveedor_nombre: str
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True



class ProductosListResponse(BaseModel):
    total: int
    page: int
    page_size: int
    total_pages: int
    productos: List[ProductoResponse] 


class MobileProducto(BaseModel):
    id: str
    nombre: str
    categoria: str
    imagen_url: Optional[str] 
    stock_disponible: int
    disponible: bool
    precio_unitario: str 
    unidad_medida: str 
    descripcion: Optional[str] = None
    
    class Config:
        from_attributes = True
        populate_by_name = True

class MobileProductoResponse(BaseModel):
    total: int
    productos: List[MobileProducto]
class GetProductosByIdsRequest(BaseModel):
    ids: list[str] = Field(..., description="Lista de IDs de productos a consultar")


class FilterProductosRequest(BaseModel):
    nombre: Optional[str] = Field(None, description="Búsqueda parcial por nombre (case-insensitive)")
    sku: Optional[str] = Field(None, description="Búsqueda exacta por SKU")
    categoria: Optional[str] = Field(None, description="Búsqueda exacta por categoría")
    text_search: Optional[str] = Field(None, description="Búsqueda parcial en nombre o SKU (case-insensitive)")


class FilterProductosResponse(BaseModel):
    producto_ids: List[str] = Field(..., description="Lista de IDs de productos que coinciden con los filtros")


class BulkUploadError(BaseModel):
    row: int
    error: str
    data: Optional[Dict] = None


class MissingFieldError(BaseModel):
    row: int
    missing_fields: List[str]


class BulkUploadValidationError(BaseModel):
    message: str
    missing_data: List[MissingFieldError]


class BulkUploadResponse(BaseModel):
    total_rows: int
    successful: int
    failed: int
    created: int = Field(default=0, description="Productos creados")
    updated: int = Field(default=0, description="Productos actualizados")
    skipped_duplicates: int = Field(default=0, description="Filas duplicadas ignoradas")
    duplicate_rows: List[int] = Field(default_factory=list, description="Números de fila duplicados")
    errors: List[BulkUploadError]
    created_products: List[str] = Field(default_factory=list, description="IDs de productos creados")
    updated_products: List[str] = Field(default_factory=list, description="IDs de productos actualizados")
