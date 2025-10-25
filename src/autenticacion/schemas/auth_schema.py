from pydantic import BaseModel, EmailStr, Field, field_validator
from typing import Optional
from datetime import datetime
from uuid import UUID


class RegisterRequest(BaseModel):
    """
    Schema para el request de registro de usuario

    Attributes:
        email: Email del usuario (validado automáticamente)
        username: Nombre para mostrar (ej: "Juan Pérez")
        password: Contraseña en texto plano (se hasheará en el servicio)
        role: Rol del usuario ('seller' o 'client')
        id_client: ID del cliente (requerido cuando role='client')
        id_seller: ID del vendedor (requerido cuando role='seller')
    """
    email: EmailStr = Field(..., description="Email del usuario")
    username: str = Field(..., min_length=2, max_length=100, description="Nombre para mostrar")
    password: str = Field(..., min_length=8, description="Contraseña (mínimo 8 caracteres)")
    role: str = Field(..., description="Rol del usuario ('seller' o 'client')")
    id_client: Optional[UUID] = Field(default=None, description="ID del cliente (requerido si role='client')")
    id_seller: Optional[UUID] = Field(default=None, description="ID del vendedor (requerido si role='seller')")

    @field_validator('role')
    @classmethod
    def validate_role(cls, v):
        """Valida que el rol sea 'seller' o 'client'"""
        if v not in ['seller', 'client']:
            raise ValueError("El rol debe ser 'seller' o 'client'")
        return v

    def model_post_init(self, __context):
        """Valida que los IDs requeridos estén presentes según el rol"""
        if self.role == 'seller' and not self.id_seller:
            raise ValueError("id_seller es requerido cuando el rol es 'seller'")
        if self.role == 'client' and not self.id_client:
            raise ValueError("id_client es requerido cuando el rol es 'client'")

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "email": "juan.perez@ejemplo.com",
                    "username": "Juan Pérez",
                    "password": "MiPassword123!",
                    "role": "seller",
                    "id_seller": "123e4567-e89b-12d3-a456-426614174000"
                },
                {
                    "email": "maria.garcia@ejemplo.com",
                    "username": "María García",
                    "password": "MiPassword456!",
                    "role": "client",
                    "id_client": "987e6543-e89b-12d3-a456-426614174111"
                }
            ]
        }
    }


class LoginRequest(BaseModel):
    """
    Schema para el request de login

    Attributes:
        email: Email del usuario
        password: Contraseña en texto plano
    """
    email: EmailStr = Field(..., description="Email del usuario")
    password: str = Field(..., description="Contraseña")

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "email": "juan.perez@ejemplo.com",
                    "password": "MiPassword123!"
                }
            ]
        }
    }


class TokenResponse(BaseModel):
    """
    Schema para la respuesta con token JWT

    Attributes:
        access_token: El token JWT generado
        token_type: Tipo de token (siempre "bearer")
    """
    access_token: str = Field(..., description="Token JWT")
    token_type: str = Field(default="bearer", description="Tipo de token")

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                    "token_type": "bearer"
                }
            ]
        }
    }


class UserResponse(BaseModel):
    """
    Schema para la respuesta con información del usuario

    IMPORTANTE: NO incluye la contraseña hasheada por seguridad

    Attributes:
        id: UUID del usuario
        email: Email del usuario
        username: Nombre para mostrar
        role: Rol del usuario ('seller' o 'client')
        id_client: ID del cliente (presente si role='client')
        id_seller: ID del vendedor (presente si role='seller')
        is_active: Si el usuario está activo
        created_at: Fecha de creación
        updated_at: Fecha de última actualización
    """
    id: str = Field(..., description="UUID del usuario")
    email: str = Field(..., description="Email del usuario")
    username: str = Field(..., description="Nombre para mostrar")
    role: Optional[str] = Field(None, description="Rol del usuario (ej: 'seller', 'client')")
    id_client: Optional[UUID] = Field(None, description="ID del cliente asociado (opcional)")
    id_seller: Optional[UUID] = Field(None, description="ID del vendedor asociado (opcional)")
    is_active: bool = Field(..., description="Si el usuario está activo")
    created_at: datetime = Field(..., description="Fecha de creación")
    updated_at: datetime = Field(..., description="Fecha de última actualización")

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "id": "123e4567-e89b-12d3-a456-426614174000",
                    "email": "juan.perez@ejemplo.com",
                    "username": "Juan Pérez",
                    "role": "seller",
                    "id_seller": "123e4567-e89b-12d3-a456-426614174000",
                    "is_active": True,
                    "created_at": "2024-01-15T10:30:00Z",
                    "updated_at": "2024-01-15T10:30:00Z"
                }
            ]
        }
    }
