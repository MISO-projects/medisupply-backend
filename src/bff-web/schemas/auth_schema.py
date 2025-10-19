from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from datetime import datetime


class RegisterRequest(BaseModel):
    """
    Schema para el request de registro de usuario

    Attributes:
        email: Email del usuario (validado automáticamente)
        username: Nombre para mostrar (ej: "Juan Pérez")
        password: Contraseña en texto plano (se hasheará en el servicio)
    """
    email: EmailStr = Field(..., description="Email del usuario")
    username: str = Field(..., min_length=2, max_length=100, description="Nombre para mostrar")
    password: str = Field(..., min_length=8, description="Contraseña (mínimo 8 caracteres)")
    role: Optional[str] = 'seller'

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "email": "juan.perez@ejemplo.com",
                    "username": "Juan Pérez",
                    "password": "MiPassword123!"
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
        is_active: Si el usuario está activo
        created_at: Fecha de creación
        updated_at: Fecha de última actualización
    """
    id: str = Field(..., description="UUID del usuario")
    email: str = Field(..., description="Email del usuario")
    username: str = Field(..., description="Nombre para mostrar")
    role: Optional[str] = Field(None, description="Rol del usuario (ej: 'seller', 'client')")
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
                    "is_active": True,
                    "created_at": "2024-01-15T10:30:00Z",
                    "updated_at": "2024-01-15T10:30:00Z"
                }
            ]
        }
    }
