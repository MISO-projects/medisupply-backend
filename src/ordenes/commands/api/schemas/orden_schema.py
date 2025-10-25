from pydantic import Field, BaseModel
from typing import List, Optional
from uuid import UUID


class DetalleOrdenSchema(BaseModel):
    id_producto: UUID = Field(..., description="ID del producto (UUID válido)")
    cantidad: int = Field(..., gt=0, description="Cantidad (debe ser mayor a 0)")
    precio_unitario: float = Field(..., gt=0, description="Precio unitario (debe ser mayor a 0)")
    observaciones: Optional[str] = Field(None, description="Observaciones")


class CrearOrdenSchema(BaseModel):
    observaciones: str = Field(..., description="Observaciones")
    id_cliente: UUID = Field(..., description="ID del cliente (UUID válido)")
    id_vendedor: UUID = Field(..., description="ID del vendedor (UUID válido)")
    detalles: List[DetalleOrdenSchema] = Field(
        ..., 
        min_length=1,
        description="Detalles de la orden (debe tener al menos un detalle)"
    )
