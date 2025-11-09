from typing import Any, Dict, List, Optional
from datetime import datetime
from pydantic import BaseModel


class OrderSummary(BaseModel):
    id: str
    numero_orden: str
    fecha_creacion: datetime
    estado: str
    valor_total: float
    id_cliente: str
    nombre_cliente: Optional[str] = None
    id_vendedor: str
    nombre_vendedor: Optional[str] = None
    cantidad_items: int
    fecha_entrega_estimada: datetime


class OrderItemDetail(BaseModel):
    id: str
    fecha_creacion: datetime
    fecha_actualizacion: datetime
    id_orden: str
    id_producto: str
    cantidad: int
    precio_unitario: float
    subtotal: float
    observaciones: Optional[str] = None


class OrderDetail(BaseModel):
    id: str
    numero_orden: str
    fecha_creacion: datetime
    fecha_actualizacion: datetime
    fecha_entrega_estimada: datetime
    estado: str
    valor_total: float
    id_cliente: str
    nombre_cliente: Optional[str] = None
    id_vendedor: str
    nombre_vendedor: Optional[str] = None
    creado_por: str
    cantidad_items: int
    observaciones: Optional[str] = None
    detalles: List[OrderItemDetail]


class PaginatedOrders(BaseModel):
    data: List[OrderDetail]
    total: int
    page: int
    page_size: int
    total_pages: int


class PaginatedClientOrders(BaseModel):
    data: List[OrderSummary]
    total: int
    page: int
    page_size: int
    total_pages: int


class SingleOrderResponse(BaseModel):
    data: OrderDetail


class IdsResponse(BaseModel):
    data: List[str]


class CacheHealthResponse(BaseModel):
    health: Dict[str, Any]
    stats: Dict[str, Any]


class CacheInvalidationResponse(BaseModel):
    status: str
    invalidated: Optional[List[str]] = None
    event_type: Optional[str] = None
    order_id: Optional[str] = None
    client_id: Optional[str] = None
    reason: Optional[str] = None


