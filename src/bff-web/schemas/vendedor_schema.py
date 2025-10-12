from pydantic import Field, BaseModel, EmailStr, field_validator
from typing import Optional
from enum import Enum
from decimal import Decimal


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
    plan_venta: Optional[str] = Field(
        None,
        description="ID del plan de venta asignado"
    )
    meta_venta: Optional[Decimal] = Field(
        None,
        ge=0,
        description="Meta de ventas en monto monetario"
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
                "plan_venta": "plan-123",
                "meta_venta": 50000.00
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
    plan_venta: Optional[str] = Field(
        None,
        description="ID del plan de venta asignado"
    )
    meta_venta: Optional[Decimal] = Field(
        None,
        ge=0,
        description="Meta de ventas en monto monetario"
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
                "meta_venta": 75000.00
            }
        }
