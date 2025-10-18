from pydantic import BaseModel, Field
from typing import Optional
from decimal import Decimal
from uuid import UUID


class CrearProductoSchema(BaseModel):
    """Schema para crear un nuevo producto"""
    nombre: str = Field(..., min_length=1, max_length=255, description="Nombre del producto")
    descripcion: Optional[str] = Field(None, description="Descripción del producto")
    categoria: str = Field(..., min_length=1, max_length=100, description="Categoría del producto")
    imagen_url: Optional[str] = Field(None, max_length=500, description="URL de la imagen del producto")
    precio_unitario: Decimal = Field(..., gt=0, description="Precio unitario del producto")
    stock_disponible: Optional[int] = Field(None, ge=0, description="Cantidad disponible en stock")
    disponible: bool = Field(True, description="Indica si el producto está disponible para venta")
    unidad_medida: str = Field(..., min_length=1, max_length=50, description="Unidad de medida (UNIDAD, CAJA, LITRO, etc)")
    sku: Optional[str] = Field(None, max_length=100, description="SKU del producto")
    tipo_almacenamiento: str = Field(..., min_length=1, max_length=50, description="Tipo de almacenamiento (AMBIENTE, REFRIGERADO, CONGELADO, etc)")
    observaciones: Optional[str] = Field(None, description="Observaciones adicionales del producto")
    proveedor_id: UUID = Field(..., description="ID del proveedor")

    class Config:
        json_schema_extra = {
            "example": {
                "nombre": "Paracetamol 500mg",
                "descripcion": "Analgésico y antipirético",
                "categoria": "MEDICAMENTOS",
                "imagen_url": "https://example.com/paracetamol.jpg",
                "precio_unitario": 15.50,
                "stock_disponible": 100,
                "disponible": True,
                "unidad_medida": "CAJA",
                "sku": "PRD-20241018-ABC12",
                "tipo_almacenamiento": "AMBIENTE",
                "observaciones": "Mantener en lugar fresco y seco",
                "proveedor_id": "550e8400-e29b-41d4-a716-446655440000"
            }
        }

