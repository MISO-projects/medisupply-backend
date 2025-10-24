from pydantic import BaseModel, Field, field_validator
from typing import Optional
from datetime import datetime


class ConductorCreateRequest(BaseModel):
    """Schema para crear un conductor"""
    nombre: str = Field(..., min_length=1, max_length=255, description="Nombre del conductor")
    apellido: str = Field(..., min_length=1, max_length=255, description="Apellido del conductor")
    documento: str = Field(..., min_length=1, max_length=50, description="Número de documento")
    telefono: Optional[str] = Field(None, max_length=20, description="Teléfono de contacto")
    email: Optional[str] = Field(None, max_length=255, description="Email del conductor")
    licencia_conducir: str = Field(..., min_length=1, max_length=50, description="Número de licencia")
    activo: bool = Field(default=True, description="Estado activo/inactivo")

    @field_validator('nombre', 'apellido', 'documento', 'licencia_conducir')
    @classmethod
    def validate_not_empty(cls, v: str, info) -> str:
        if not v or not v.strip():
            raise ValueError(f'{info.field_name} no puede estar vacío')
        return v.strip()

    class Config:
        json_schema_extra = {
            "example": {
                "nombre": "Juan",
                "apellido": "Pérez",
                "documento": "1234567890",
                "telefono": "3001234567",
                "email": "juan.perez@medisupply.com",
                "licencia_conducir": "C2-12345678",
                "activo": True
            }
        }


class ConductorUpdateRequest(BaseModel):
    """Schema para actualizar un conductor"""
    nombre: Optional[str] = Field(None, min_length=1, max_length=255)
    apellido: Optional[str] = Field(None, min_length=1, max_length=255)
    documento: Optional[str] = Field(None, min_length=1, max_length=50)
    telefono: Optional[str] = Field(None, max_length=20)
    email: Optional[str] = Field(None, max_length=255)
    licencia_conducir: Optional[str] = Field(None, min_length=1, max_length=50)
    activo: Optional[bool] = None

    @field_validator('nombre', 'apellido', 'documento', 'licencia_conducir')
    @classmethod
    def validate_not_empty(cls, v: str, info) -> str:
        if v is not None and (not v or not v.strip()):
            raise ValueError(f'{info.field_name} no puede estar vacío')
        return v.strip() if v else v

    class Config:
        json_schema_extra = {
            "example": {
                "telefono": "3109876543",
                "email": "juan.perez.nuevo@medisupply.com",
                "activo": False
            }
        }


class ConductorResponse(BaseModel):
    """Schema para la respuesta de un conductor"""
    id: int
    nombre: str
    apellido: str
    nombre_completo: str
    documento: str
    telefono: Optional[str]
    email: Optional[str]
    licencia_conducir: str
    activo: bool
    fecha_creacion: datetime
    fecha_actualizacion: datetime

    class Config:
        json_schema_extra = {
            "example": {
                "id": 1,
                "nombre": "Juan",
                "apellido": "Pérez",
                "nombre_completo": "Juan Pérez",
                "documento": "1234567890",
                "telefono": "3001234567",
                "email": "juan.perez@medisupply.com",
                "licencia_conducir": "C2-12345678",
                "activo": True,
                "fecha_creacion": "2025-10-24T10:00:00Z",
                "fecha_actualizacion": "2025-10-24T10:00:00Z"
            }
        }


class ConductoresListResponse(BaseModel):
    """Schema para la respuesta de listado de conductores"""
    total: int
    page: int
    page_size: int
    total_pages: int
    conductores: list[ConductorResponse]

    class Config:
        json_schema_extra = {
            "example": {
                "total": 10,
                "page": 1,
                "page_size": 10,
                "total_pages": 1,
                "conductores": []
            }
        }

