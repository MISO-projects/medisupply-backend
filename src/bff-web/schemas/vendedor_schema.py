from pydantic import Field, BaseModel, EmailStr, field_validator
from typing import Optional
from enum import Enum
from uuid import UUID


class ZonaAsignadaEnum(str, Enum):
    COLOMBIA = "Colombia"
    PERU = "Perú"
    ECUADOR = "Ecuador"
    MEXICO = "México"


class CrearVendedorSchema(BaseModel):
    nombre: str = Field(
        ...,
        min_length=1,
        max_length=255,
        description="Nombre completo del vendedor"
    )
    documento_identidad: str = Field(
        ...,
        min_length=1,
        description="Documento de identidad del vendedor"
    )
    email: EmailStr = Field(
        ...,
        description="Email del vendedor"
    )
    zona_asignada: ZonaAsignadaEnum = Field(
        ...,
        description="Zona/país asignado al vendedor"
    )
    plan_venta_id: UUID = Field(
        ...,
        description="ID (UUID) del plan de venta al que está asignado el vendedor"
    )

    @field_validator('nombre')
    @classmethod
    def validate_nombre(cls, v: str) -> str:
        """Valida que el nombre no sea una cadena vacía"""
        if v.strip() == '':
            raise ValueError('El nombre no puede estar vacío')
        return v.strip()

    @field_validator('documento_identidad')
    @classmethod
    def validate_documento(cls, v: str) -> str:
        """Valida que el documento no sea una cadena vacía"""
        if v.strip() == '':
            raise ValueError('El documento de identidad no puede estar vacío')
        return v.strip()

    class Config:
        json_schema_extra = {
            "example": {
                "nombre": "Juan Pérez",
                "documento_identidad": "12345678",
                "email": "juan.perez@medisupply.com",
                "zona_asignada": "Perú",
                "plan_venta_id": "550e8400-e29b-41d4-a716-446655440000"
            }
        }


class ActualizarVendedorSchema(BaseModel):
    nombre: Optional[str] = Field(
        None,
        min_length=1,
        max_length=255,
        description="Nombre completo del vendedor"
    )
    email: Optional[EmailStr] = Field(
        None,
        description="Email del vendedor"
    )
    zona_asignada: Optional[ZonaAsignadaEnum] = Field(
        None,
        description="Zona/país asignado al vendedor"
    )
    plan_venta_id: Optional[UUID] = Field(
        None,
        description="ID (UUID) del plan de venta asignado"
    )

    @field_validator('nombre')
    @classmethod
    def validate_nombre(cls, v: Optional[str]) -> Optional[str]:
        """Valida que el nombre no sea una cadena vacía"""
        if v is not None and v.strip() == '':
            raise ValueError('El nombre no puede estar vacío')
        return v.strip() if v else v

    @field_validator('email')
    @classmethod
    def validate_email(cls, v: Optional[EmailStr]) -> Optional[EmailStr]:
        """Valida que el email no sea una cadena vacía"""
        if v is not None and v.strip() == '':
            raise ValueError('El email no puede estar vacío')
        return v.strip() if v else v

    class Config:
        json_schema_extra = {
            "example": {
                "nombre": "Juan Pérez",
                "email": "juan.nuevo@medisupply.com",
                "zona_asignada": "Colombia",
                "plan_venta_id": "550e8400-e29b-41d4-a716-446655440000"
            }
        }
