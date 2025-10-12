from pydantic import Field, BaseModel, EmailStr, field_validator, model_validator
from datetime import datetime
from typing import Optional
from enum import Enum
import re


class PaisEnum(str, Enum):
    COLOMBIA = "Colombia"
    PERU = "Perú"
    ECUADOR = "Ecuador"
    MEXICO = "México"


class TipoProveedorEnum(str, Enum):
    FABRICANTE = "Fabricante"
    DISTRIBUIDOR = "Distribuidor"
    MAYORISTA = "Mayorista"
    IMPORTADOR = "Importador"
    MINORISTA = "Minorista"


class CrearProveedorSchema(BaseModel):
    nombre: str = Field(
        ...,
        min_length=1,
        max_length=255,
        description="Nombre del proveedor"
    )
    id_tributario: str = Field(
        ...,
        min_length=1,
        description="ID tributario del proveedor (RUC/NIT/RFC según país)"
    )
    tipo_proveedor: TipoProveedorEnum = Field(
        ...,
        description="Tipo de proveedor"
    )
    email: EmailStr = Field(
        ...,
        description="Email del proveedor"
    )
    pais: PaisEnum = Field(
        ...,
        description="País del proveedor"
    )
    contacto: Optional[str] = Field(
        None,
        max_length=255,
        description="Contacto del proveedor"
    )
    condiciones_entrega: Optional[str] = Field(
        None,
        max_length=500,
        description="Condiciones de entrega. Ej. Entrega en 5 días hábiles, cobertura nacional"
    )

    @model_validator(mode='after')
    def validate_id_tributario(self):
        """
        Valida el formato del ID tributario según el país:
        - RUC (Perú): 11 dígitos
        - NIT (Colombia): 9-10 dígitos
        - RFC (México): 12-13 caracteres alfanuméricos
        """
        id_trib = self.id_tributario.strip()
        pais = self.pais
        
        if pais == PaisEnum.PERU:
            # RUC: 11 dígitos
            if not re.match(r'^\d{11}$', id_trib):
                raise ValueError('RUC debe tener 11 dígitos numéricos')
        elif pais == PaisEnum.COLOMBIA:
            # NIT: 9-10 dígitos
            if not re.match(r'^\d{9,10}$', id_trib):
                raise ValueError('NIT debe tener 9 o 10 dígitos numéricos')
        elif pais == PaisEnum.MEXICO:
            # RFC: 12-13 caracteres alfanuméricos
            if not re.match(r'^[A-ZÑ&]{3,4}\d{6}[A-Z0-9]{3}$', id_trib.upper()):
                raise ValueError('RFC debe tener formato válido (12-13 caracteres alfanuméricos)')
            self.id_tributario = id_trib.upper()
        elif pais == PaisEnum.ECUADOR:
            # RUC Ecuador: 13 dígitos
            if not re.match(r'^\d{13}$', id_trib):
                raise ValueError('RUC debe tener 13 dígitos numéricos')
        
        # Update with trimmed value
        self.id_tributario = id_trib
        return self

    @field_validator('nombre', 'contacto')
    @classmethod
    def validate_no_empty_strings(cls, v: Optional[str]) -> Optional[str]:
        """Valida que los campos de texto no sean strings vacíos"""
        if v is not None and v.strip() == '':
            raise ValueError('El campo no puede estar vacío')
        return v.strip() if v else v

    class Config:
        json_schema_extra = {
            "example": {
                "nombre": "Farmacéutica Nacional S.A.",
                "id_tributario": "20123456789",
                "tipo_proveedor": "Fabricante",
                "email": "contacto@farmaceutica.com",
                "pais": "Perú",
                "contacto": "Juan Pérez - +51 999 888 777",
                "condiciones_entrega": "Entrega en 5 días hábiles, cobertura nacional"
            }
        }


class ActualizarProveedorSchema(BaseModel):
    nombre: Optional[str] = Field(
        None,
        min_length=1,
        max_length=255,
        description="Nombre del proveedor"
    )
    tipo_proveedor: Optional[TipoProveedorEnum] = Field(
        None,
        description="Tipo de proveedor"
    )
    email: Optional[EmailStr] = Field(
        None,
        description="Email del proveedor"
    )
    contacto: Optional[str] = Field(
        None,
        max_length=255,
        description="Contacto del proveedor"
    )
    condiciones_entrega: Optional[str] = Field(
        None,
        max_length=500,
        description="Condiciones de entrega"
    )

    @field_validator('nombre', 'contacto')
    @classmethod
    def validate_no_empty_strings(cls, v: Optional[str]) -> Optional[str]:
        """Valida que los campos de texto no sean strings vacíos"""
        if v is not None and v.strip() == '':
            raise ValueError('El campo no puede estar vacío')
        return v.strip() if v else v

    class Config:
        json_schema_extra = {
            "example": {
                "nombre": "Farmacéutica Nacional S.A.C.",
                "email": "nuevo@farmaceutica.com",
                "contacto": "María García - +51 999 777 888"
            }
        }

