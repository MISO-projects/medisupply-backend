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
