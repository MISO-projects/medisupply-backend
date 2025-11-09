from pydantic import Field, BaseModel
from typing import List, Optional, Any, Dict
from uuid import UUID


class DetalleOrdenRequest(BaseModel):
    """Schema para un detalle de orden en la solicitud"""
    id_producto: UUID = Field(..., description="ID del producto (UUID válido)")
    cantidad: int = Field(..., gt=0, description="Cantidad (debe ser mayor a 0)")
    precio_unitario: float = Field(..., gt=0, description="Precio unitario (debe ser mayor a 0)")
    observaciones: Optional[str] = Field(None, description="Observaciones del detalle")

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "id_producto": "123e4567-e89b-12d3-a456-426614174000",
                    "cantidad": 10,
                    "precio_unitario": 25.50,
                    "observaciones": "Urgente"
                }
            ]
        }
    }


class CrearOrdenRequest(BaseModel):
    """Schema para crear una nueva orden"""
    observaciones: Optional[str] = Field(None, description="Observaciones generales de la orden")
    id_cliente: UUID = Field(..., description="ID del cliente (UUID válido)")
    id_vendedor: UUID = Field(..., description="ID del vendedor (UUID válido)")
    detalles: List[DetalleOrdenRequest] = Field(
        ..., 
        min_length=1,
        description="Detalles de la orden (debe tener al menos un detalle)"
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "observaciones": "Pedido urgente - Entregar en recepción",
                    "id_cliente": "123e4567-e89b-12d3-a456-426614174000",
                    "id_vendedor": "987fcdeb-51a2-43c7-9876-543210fedcba",
                    "detalles": [
                        {
                            "id_producto": "456e7890-e89b-12d3-a456-426614174111",
                            "cantidad": 10,
                            "precio_unitario": 25.50,
                            "observaciones": "Lote reciente"
                        }
                    ]
                }
            ]
        }
    }


class CrearOrdenResponse(BaseModel):
    """Schema para la respuesta al crear una orden"""
    id: UUID = Field(..., description="ID de la orden creada (UUID)")
    numero_orden: str = Field(..., description="Número de orden generado")

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "id": "123e4567-e89b-12d3-a456-426614174000",
                    "numero_orden": "ORD-251025-A1B2C3D4"
                }
            ]
        }
    }


class CrearOrdenClienteRequest(BaseModel):
    """Schema para que clientes creen sus propias órdenes (BFF Mobile)"""
    observaciones: Optional[str] = Field(None, description="Observaciones generales de la orden")
    detalles: List[DetalleOrdenRequest] = Field(
        ..., 
        min_length=1,
        description="Detalles de la orden (debe tener al menos un detalle)"
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "observaciones": "Pedido urgente - Entregar en recepción",
                    "detalles": [
                        {
                            "id_producto": "456e7890-e89b-12d3-a456-426614174111",
                            "cantidad": 10,
                            "precio_unitario": 25.50,
                            "observaciones": "Lote reciente"
                        }
                    ]
                }
            ]
        }
    }


class OrdenResumen(BaseModel):
    """Schema de resumen de orden (BFF)"""
    id: str
    numero_orden: str
    fecha_creacion: str
    estado: str
    valor_total: float
    id_cliente: str
    cantidad_items: int
    fecha_entrega_estimada: str
    nombre_cliente: Optional[str] = None


class OrdenDetalle(BaseModel):
    """Schema de detalle de orden (BFF)"""
    id: str
    numero_orden: str
    fecha_creacion: str
    fecha_actualizacion: str
    fecha_entrega_estimada: str
    estado: str
    valor_total: float
    id_cliente: str
    id_vendedor: str
    creado_por: str
    cantidad_items: int
    observaciones: Optional[str] = None
    detalles: List["DetalleOrdenRespuesta"]
    nombre_cliente: Optional[str] = None
    direccion_cliente: Optional[str] = None


class PaginadoOrdenes(BaseModel):
    data: List[OrdenDetalle]
    total: int
    page: int
    page_size: int
    total_pages: int


class PaginadoOrdenesCliente(BaseModel):
    data: List[OrdenResumen]
    total: int
    page: int
    page_size: int
    total_pages: int


class RespuestaOrden(BaseModel):
    data: OrdenDetalle


class DetalleOrdenRespuesta(BaseModel):
    """Schema para un detalle de orden en la respuesta (BFF)"""
    id: str
    fecha_creacion: str
    fecha_actualizacion: str
    id_orden: str
    id_producto: str
    cantidad: int
    precio_unitario: float
    subtotal: float
    observaciones: Optional[str] = None
    nombre_producto: Optional[str] = None


class EntregaProgramadaParada(BaseModel):
    """Schema de parada de entrega"""
    id: int
    pedido_id: str
    direccion: str
    contacto: str
    latitud: Optional[float] = None
    longitud: Optional[float] = None
    orden: Optional[int] = None
    estado: str
    fecha_creacion: str
    fecha_actualizacion: str


class EntregaProgramadaRuta(BaseModel):
    """Schema de ruta de entrega"""
    id: int
    fecha: str
    bodega_origen: str
    estado: str
    vehiculo_placa: Optional[str] = None
    vehiculo_info: Optional[str] = None
    conductor_nombre: Optional[str] = None
    condiciones_almacenamiento: Optional[str] = None


class EntregaProgramadaPedido(BaseModel):
    """Schema de pedido en entrega"""
    numero_orden: str
    estado: str
    valor_total: Optional[float] = None
    cantidad_items: int
    nombre_cliente: Optional[str] = None


class EntregaProgramada(BaseModel):
    """Schema completo de entrega programada"""
    parada: EntregaProgramadaParada
    pedido: Optional[EntregaProgramadaPedido] = None
    ruta: Optional[EntregaProgramadaRuta] = None


class PaginadoEntregasProgramadas(BaseModel):
    """Schema paginado de entregas programadas"""
    data: List[EntregaProgramada]
    total: int
    page: int
    page_size: int
    total_pages: int
