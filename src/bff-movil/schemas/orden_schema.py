from pydantic import Field, BaseModel
from typing import List, Optional
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

