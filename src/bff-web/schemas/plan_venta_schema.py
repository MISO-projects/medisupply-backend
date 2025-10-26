from pydantic import Field, BaseModel, field_validator
from typing import Optional
from datetime import datetime
from decimal import Decimal

from .vendedor_schema import ZonaAsignadaEnum


class CrearPlanVentaSchema(BaseModel):
    """
    Schema para crear un nuevo plan de venta.

    Valida todos los campos requeridos y opcionales al crear un plan.
    """
    nombre: str = Field(
        ...,
        min_length=1,
        max_length=255,
        description="Nombre descriptivo del plan de venta (debe ser único)"
    )
    fecha_inicio: datetime = Field(
        ...,
        description="Fecha de inicio del plan de venta"
    )
    fecha_fin: datetime = Field(
        ...,
        description="Fecha de finalización del plan de venta"
    )
    descripcion: Optional[str] = Field(
        None,
        description="Descripción detallada del plan (opcional)"
    )
    meta_venta: Decimal = Field(
        ...,
        gt=0,
        decimal_places=2,
        description="Meta de ventas en monto monetario (debe ser mayor a 0)"
    )
    zona_asignada: Optional[ZonaAsignadaEnum] = Field(
        None,
        description="Zona geográfica asignada al plan (opcional)"
    )

    @field_validator('nombre')
    @classmethod
    def validate_nombre(cls, v: str) -> str:
        """Valida que el nombre no sea una cadena vacía"""
        if v.strip() == '':
            raise ValueError('El nombre no puede estar vacío')
        return v.strip()

    @field_validator('descripcion')
    @classmethod
    def validate_descripcion(cls, v: Optional[str]) -> Optional[str]:
        """Valida y limpia la descripción si se proporciona"""
        if v is not None and v.strip() == '':
            return None  # Convertir cadenas vacías a None
        return v.strip() if v else None

    @field_validator('fecha_fin')
    @classmethod
    def validate_fechas(cls, v: datetime, info) -> datetime:
        """
        Valida que la fecha_fin sea posterior a fecha_inicio.

        Esta validación solo se ejecuta si fecha_inicio ya fue procesada.
        """
        if 'fecha_inicio' in info.data:
            fecha_inicio = info.data['fecha_inicio']
            if v <= fecha_inicio:
                raise ValueError('La fecha_fin debe ser posterior a la fecha_inicio')
        return v

    class Config:
        json_schema_extra = {
            "example": {
                "nombre": "Plan Q1 2024 - Perú",
                "fecha_inicio": "2024-01-01T00:00:00",
                "fecha_fin": "2024-03-31T23:59:59",
                "descripcion": "Plan de ventas del primer trimestre para la región de Perú",
                "meta_venta": 100000.00,
                "zona_asignada": "Perú"
            }
        }


class ActualizarPlanVentaSchema(BaseModel):
    """
    Schema para actualizar un plan de venta existente.

    Todos los campos son opcionales - solo se actualizan los enviados.
    """
    nombre: Optional[str] = Field(
        None,
        min_length=1,
        max_length=255,
        description="Nombre descriptivo del plan de venta (debe ser único)"
    )
    fecha_inicio: Optional[datetime] = Field(
        None,
        description="Fecha de inicio del plan de venta"
    )
    fecha_fin: Optional[datetime] = Field(
        None,
        description="Fecha de finalización del plan de venta"
    )
    descripcion: Optional[str] = Field(
        None,
        description="Descripción detallada del plan"
    )
    meta_venta: Optional[Decimal] = Field(
        None,
        gt=0,
        decimal_places=2,
        description="Meta de ventas en monto monetario"
    )
    zona_asignada: Optional[ZonaAsignadaEnum] = Field(
        None,
        description="Zona geográfica asignada al plan"
    )

    @field_validator('nombre')
    @classmethod
    def validate_nombre(cls, v: Optional[str]) -> Optional[str]:
        """Valida que el nombre no sea una cadena vacía"""
        if v is not None and v.strip() == '':
            raise ValueError('El nombre no puede estar vacío')
        return v.strip() if v else v

    @field_validator('descripcion')
    @classmethod
    def validate_descripcion(cls, v: Optional[str]) -> Optional[str]:
        """Valida y limpia la descripción"""
        if v is not None and v.strip() == '':
            return None
        return v.strip() if v else None

    class Config:
        json_schema_extra = {
            "example": {
                "nombre": "Plan Q1 2024 - Perú (Actualizado)",
                "meta_venta": 150000.00,
                "descripcion": "Meta incrementada debido a buen desempeño"
            }
        }
