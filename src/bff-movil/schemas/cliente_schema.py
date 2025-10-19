from pydantic import BaseModel, Field, field_validator
from typing import Optional
from datetime import datetime


class ClienteAsignadoResponse(BaseModel):
    id: str = Field(..., min_length=1, description="Identificador único del cliente")
    nombre: str = Field(..., min_length=1, description="Nombre de la institución")
    nit: str = Field(..., min_length=1, description="Número de identificación tributaria")
    logoUrl: Optional[str] = Field(None, description="URL del logo de la institución")
    
    @field_validator('id', 'nombre', 'nit')
    @classmethod
    def validate_not_empty(cls, v: str, info) -> str:
        """Valida que los campos no sean strings vacíos"""
        if not v or not v.strip():
            raise ValueError(f'{info.field_name} no puede estar vacío')
        return v.strip()

    class Config:
        json_schema_extra = {
            "example": {
                "id": "C001",
                "nombre": "Hospital General",
                "nit": "901234567-8",
                "logoUrl": "https://storage.googleapis.com/logos/hospital-general.png"
            }
        }


class ClienteAsignadoListResponse(BaseModel):
    clientes: list[ClienteAsignadoResponse] = Field(..., description="Lista de clientes asignados")
    total: int = Field(..., description="Total de clientes asignados")

    class Config:
        json_schema_extra = {
            "example": {
                "clientes": [
                    {
                        "id": "C001",
                        "nombre": "Hospital General",
                        "nit": "901234567-8",
                        "logoUrl": "https://storage.googleapis.com/logos/hospital-general.png"
                    },
                    {
                        "id": "C002",
                        "nombre": "Clinica San Martin",
                        "nit": "901987654-3",
                        "logoUrl": "https://storage.googleapis.com/logos/clinica-san-martin.png"
                    }
                ],
                "total": 2
            }
        }


class ClientResponse(BaseModel):
    """
    Schema para la respuesta con información del cliente

    Attributes:
        id: UUID del usuario
        nombre: Nombre para mostrar
        created_at: Fecha de creación
        updated_at: Fecha de última actualización

        "id": str(self.id),
            "nombre": self.nombre,
            "nit": self.nit,
            "logoUrl": self.logo_url,
            "address": self.address,
            "fecha_creacion": self.fecha_creacion.isoformat() if self.fecha_creacion else None,
            "fecha_actualizacion": self.fecha_actualizacion.isoformat() if self.fecha_actualizacion else None,
            "id_vendedor": str(self.id_vendedor)


    """
    id: str = Field(..., description="Id del cliente institucional")
    nombre: str = Field(..., description="Nombre del cliente institucional")
    logoUrl: str = Field(..., description="URL del logo del cliente institucional")
    address: str = Field(..., description="Dirección del cliente institucional")
    fecha_creacion: datetime = Field(..., description=  "Fecha de creación")
    fecha_actualizacion: datetime = Field(..., description="Fecha de última actualización")
    id_vendedor: str = Field(..., description="Id del vendedor asignado")

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "id": "c123e4567-e89b-12d3-a456-426614174000",
                    "nombre": "Hospital Central",
                    "logoUrl": "https://storage.googleapis.com/logos/hospital-central.png",
                    "address": "Calle 123 #45-67, Ciudad",
                    "fecha_creacion": "2024-01-15T10:00:00Z",
                    "fecha_actualizacion": "2024-06-20T15:30:00Z",
                    "id_vendedor": "u123e4567-e89b-12d3-a456-426614174000"
                }
            ]
        }
    }

class RegisterRequest(BaseModel):
    """
    Schema para el request de registro de usuario

    Attributes:
        email: Email del usuario (validado automáticamente)
        username: Nombre para mostrar (ej: "Juan Pérez")
        password: Contraseña en texto plano (se hasheará en el servicio)

        {
	
    "nombre": "Hospital General",
    "nit": "901234567-8",
    "logoUrl": "https://storage.googleapis.com/logos/hospital-general.png",
    "address": "dirección"
}
    """
    nombre: str = Field(..., min_length=1, description="Nombre del cliente institucional")
    nit: str = Field(..., min_length=1, description="Número de identificación tributaria")
    logoUrl: Optional[str] = Field(None, description="URL del logo del cliente institucional")
    address: str = Field(..., min_length=1, description="Dirección del cliente institucional")

    model_config = {
        "json_schema_extra": {
            "examples": [
                {  
                    "nombre": "Hospital General",
                    "nit": "901234567-8",
                    "logoUrl": "https://storage.googleapis.com/logos/hospital-general.png",
                    "address": "dirección"
                }
            ]
        }
    }
