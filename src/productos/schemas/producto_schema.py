from pydantic import BaseModel, Field, field_validator
from typing import Optional
from datetime import datetime
from decimal import Decimal


class ProductoBase(BaseModel):
    nombre: str = Field(..., min_length=1, max_length=255, description="Nombre del producto")
    descripcion: Optional[str] = Field(None, description="Descripción del producto")
    categoria: str = Field(..., min_length=1, max_length=100, description="Categoría del producto")
    imagen_url: Optional[str] = Field(None, max_length=500, description="URL de la imagen del producto")
    precio_unitario: Decimal = Field(..., gt=0, description="Precio unitario del producto")
    stock_disponible: int = Field(..., ge=0, description="Cantidad disponible en stock")
    disponible: bool = Field(True, description="Indica si el producto está disponible para venta")
    unidad_medida: str = Field("UNIDAD", max_length=50, description="Unidad de medida (UNIDAD, CAJA, LITRO, etc)")
    sku: Optional[str] = Field(None, max_length=100, description="SKU del producto")


class ProductoCreate(ProductoBase):
    pass


class ProductoUpdate(BaseModel):
    nombre: Optional[str] = Field(None, min_length=1, max_length=255)
    descripcion: Optional[str] = None
    categoria: Optional[str] = Field(None, min_length=1, max_length=100)
    imagen_url: Optional[str] = Field(None, max_length=500)
    precio_unitario: Optional[Decimal] = Field(None, gt=0)
    stock_disponible: Optional[int] = Field(None, ge=0)
    disponible: Optional[bool] = None
    unidad_medida: Optional[str] = Field(None, max_length=50)
    sku: Optional[str] = Field(None, max_length=100)


class ProductoResponse(ProductoBase):
    id: str
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class ProductoConStock(BaseModel):
    id: str
    nombre: str
    categoria: str
    imagen_url: Optional[str] = None
    stock_disponible: int
    disponible: bool
    precio_unitario: Decimal
    unidad_medida: str
    descripcion: Optional[str] = None

    class Config:
        from_attributes = True


class ProductosListResponse(BaseModel):
    total: int
    productos: list[ProductoConStock]

