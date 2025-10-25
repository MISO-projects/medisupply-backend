from pydantic import BaseModel, Field, field_validator
from typing import Optional
from datetime import datetime


class VehiculoCreateRequest(BaseModel):
    """Schema para crear un vehículo"""
    placa: str = Field(..., min_length=1, max_length=20, description="Placa del vehículo")
    marca: str = Field(..., min_length=1, max_length=100, description="Marca del vehículo")
    modelo: str = Field(..., min_length=1, max_length=100, description="Modelo del vehículo")
    año: Optional[int] = Field(None, ge=1900, le=2100, description="Año del vehículo")
    tipo: str = Field(..., min_length=1, max_length=50, description="Tipo de vehículo")
    capacidad_kg: Optional[int] = Field(None, ge=0, description="Capacidad en kilogramos")
    activo: bool = Field(default=True, description="Estado activo/inactivo")

    @field_validator('placa', 'marca', 'modelo', 'tipo')
    @classmethod
    def validate_not_empty(cls, v: str, info) -> str:
        if not v or not v.strip():
            raise ValueError(f'{info.field_name} no puede estar vacío')
        return v.strip()

    class Config:
        json_schema_extra = {
            "example": {
                "placa": "ABC123",
                "marca": "Chevrolet",
                "modelo": "NQR",
                "año": 2022,
                "tipo": "Camión refrigerado",
                "capacidad_kg": 3500,
                "activo": True
            }
        }


class VehiculoUpdateRequest(BaseModel):
    """Schema para actualizar un vehículo"""
    placa: Optional[str] = Field(None, min_length=1, max_length=20)
    marca: Optional[str] = Field(None, min_length=1, max_length=100)
    modelo: Optional[str] = Field(None, min_length=1, max_length=100)
    año: Optional[int] = Field(None, ge=1900, le=2100)
    tipo: Optional[str] = Field(None, min_length=1, max_length=50)
    capacidad_kg: Optional[int] = Field(None, ge=0)
    activo: Optional[bool] = None

    @field_validator('placa', 'marca', 'modelo', 'tipo')
    @classmethod
    def validate_not_empty(cls, v: str, info) -> str:
        if v is not None and (not v or not v.strip()):
            raise ValueError(f'{info.field_name} no puede estar vacío')
        return v.strip() if v else v

    class Config:
        json_schema_extra = {
            "example": {
                "capacidad_kg": 4000,
                "activo": False
            }
        }


class VehiculoResponse(BaseModel):
    """Schema para la respuesta de un vehículo"""
    id: int
    placa: str
    marca: str
    modelo: str
    año: Optional[int]
    tipo: str
    capacidad_kg: Optional[int]
    activo: bool
    fecha_creacion: datetime
    fecha_actualizacion: datetime

    class Config:
        json_schema_extra = {
            "example": {
                "id": 1,
                "placa": "ABC123",
                "marca": "Chevrolet",
                "modelo": "NQR",
                "año": 2022,
                "tipo": "Camión refrigerado",
                "capacidad_kg": 3500,
                "activo": True,
                "fecha_creacion": "2025-10-24T10:00:00Z",
                "fecha_actualizacion": "2025-10-24T10:00:00Z"
            }
        }


class VehiculosListResponse(BaseModel):
    """Schema para la respuesta de listado de vehículos"""
    total: int
    page: int
    page_size: int
    total_pages: int
    vehiculos: list[VehiculoResponse]

    class Config:
        json_schema_extra = {
            "example": {
                "total": 10,
                "page": 1,
                "page_size": 10,
                "total_pages": 1,
                "vehiculos": []
            }
        }

