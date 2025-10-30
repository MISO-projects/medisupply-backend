from datetime import datetime, date
from typing import Optional, Dict
from pydantic import BaseModel, UUID4, Field
from typing import List

class CrearRegistroInventarioSchema(BaseModel):
    """Esquema de datos requeridos para crear un nuevo registro de inventario."""
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
        from_attributes = True 

class RegistroInventarioResponseSchema(CrearRegistroInventarioSchema):
    """Esquema de datos devueltos después de crear un registro de inventario."""
    id: UUID4
    fecha_recepcion: datetime
    created_at: datetime
    updated_at: Optional[datetime]
    producto_nombre: Optional[str] = Field(None, description="Nombre del producto (enriquecido)")
    producto_sku: Optional[str] = Field(None, description="SKU del producto (enriquecido)")

    class Config:
        from_attributes = True


class StockDisponibleResponse(BaseModel):
    items: List[RegistroInventarioResponseSchema]
    total: int

class InventarioListResponse(BaseModel):
    items: List[RegistroInventarioResponseSchema]
    total: int
    page: int
    page_size: int
    total_pages: int
    
class StockBatchRequest(BaseModel):
    producto_ids: List[str] = Field(..., description="Lista de IDs de productos (UUIDs como string)")

class StockBatchResponse(BaseModel):
    stock_data: Dict[str, int] = Field(..., description="Diccionario de producto_id: stock_total")