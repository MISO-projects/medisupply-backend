from pydantic import BaseModel, Field, UUID4
from datetime import datetime, date
from typing import Optional
from decimal import Decimal
from uuid import UUID


class CrearRegistroInventarioSchema(BaseModel):
    """Schema para crear un nuevo producto"""
    producto_id: UUID4 = Field(..., description="UUID del producto al que pertenece este registro.")
    lote: str = Field(..., min_length=1, max_length=100, description="Código de lote del proveedor.")
    fecha_vencimiento: date = Field(..., description="Fecha de vencimiento de este lote (YYYY-MM-DD).")
    cantidad: int = Field(..., gt=0, description="Cantidad de unidades en este registro.")
    ubicacion: str = Field("BODEGA-PRINCIPAL", max_length=100, description="Ubicación física del stock.")
    temperatura_requerida: str = Field("AMBIENTE", max_length=50, description="Condición de temperatura del stock.")
    estado: str = Field("DISPONIBLE", max_length=50, description="Estado inicial del stock (DISPONIBLE, BLOQUEADO, etc.).")
    condiciones_especiales: Optional[str] = Field(None, description="Cualquier condición especial de manejo.")
    observaciones: Optional[str] = Field(None, description="Observaciones adicionales sobre el lote.")
 
    class Config:
        json_schema_extra = {
            "example": {
                "producto_id": "550e8400-e29b-41d4-a716-446655440000",
                "lote": "LOT-20241018-XYZ",
                "fecha_vencimiento": "2025-10-18",
                "cantidad": 500,
                "ubicacion": "A2-CORRIDOR-3",
                "temperatura_requerida": "AMBIENTE",
                "estado": "DISPONIBLE",
                "condiciones_especiales": "Mantener alejado de la luz directa",
                "observaciones": "Revisar integridad del empaque al recibir"
            }
        }

