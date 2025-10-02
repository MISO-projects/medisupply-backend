from pydantic import Field, BaseModel
from datetime import datetime
from typing import List, Optional


class DetalleOrdenSchema(BaseModel):
    id_producto: str = Field(..., description="ID del producto")
    cantidad: int = Field(..., description="Cantidad")
    precio_unitario: float = Field(..., description="Precio unitario")
    observaciones: Optional[str] = Field(None, description="Observaciones")


class CrearOrdenSchema(BaseModel):
    fecha_entrega_estimada: datetime = Field(
        ..., description="Fecha de entrega estimada"
    )
    observaciones: str = Field(..., description="Observaciones")
    id_cliente: str = Field(..., description="ID del cliente")
    id_vendedor: str = Field(..., description="ID del vendedor")
    id_bodega_origen: str = Field(..., description="ID de la bodega de origen")
    creado_por: str = Field(..., description="Usuario que creó la orden")
    detalles: List[DetalleOrdenSchema] = Field(..., description="Detalles de la orden")
    observaciones: str = Field(..., description="Observaciones")
    fecha_entrega_estimada: datetime = Field(
        ..., description="Fecha de entrega estimada"
    )
