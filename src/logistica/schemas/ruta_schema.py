from pydantic import BaseModel, Field, field_validator
from typing import Optional, List
from datetime import datetime


class ParadaRequest(BaseModel):
    """Schema para la solicitud de una parada en la ruta"""
    cliente_id: int = Field(..., description="ID del cliente", gt=0)
    direccion: str = Field(..., min_length=1, description="Dirección de la parada")
    contacto: str = Field(..., min_length=1, description="Nombre del contacto en la parada")
    latitud: Optional[float] = Field(None, description="Latitud de la ubicación", ge=-90, le=90)
    longitud: Optional[float] = Field(None, description="Longitud de la ubicación", ge=-180, le=180)
    orden: Optional[int] = Field(None, description="Orden de la parada en la ruta", ge=1)

    @field_validator('direccion', 'contacto')
    @classmethod
    def validate_not_empty(cls, v: str, info) -> str:
        """Valida que los campos no sean strings vacíos"""
        if not v or not v.strip():
            raise ValueError(f'{info.field_name} no puede estar vacío')
        return v.strip()

    class Config:
        json_schema_extra = {
            "example": {
                "cliente_id": 32,
                "direccion": "Calle 80 #45-20",
                "contacto": "Carlos Ríos",
                "latitud": 4.7110,
                "longitud": -74.0721,
                "orden": 1
            }
        }


class ParadaResponse(BaseModel):
    """Schema para la respuesta de una parada"""
    id: int = Field(..., description="ID de la parada")
    ruta_id: int = Field(..., description="ID de la ruta")
    cliente_id: int = Field(..., description="ID del cliente")
    direccion: str = Field(..., description="Dirección de la parada")
    contacto: str = Field(..., description="Nombre del contacto")
    latitud: Optional[float] = Field(None, description="Latitud de la ubicación")
    longitud: Optional[float] = Field(None, description="Longitud de la ubicación")
    orden: Optional[int] = Field(None, description="Orden de la parada")
    estado: str = Field(..., description="Estado de la parada")
    fecha_creacion: datetime = Field(..., description="Fecha de creación")
    fecha_actualizacion: datetime = Field(..., description="Fecha de actualización")

    class Config:
        json_schema_extra = {
            "example": {
                "id": 1,
                "ruta_id": 145,
                "cliente_id": 32,
                "direccion": "Calle 80 #45-20",
                "contacto": "Carlos Ríos",
                "latitud": 4.7110,
                "longitud": -74.0721,
                "orden": 1,
                "estado": "Pendiente",
                "fecha_creacion": "2025-08-17T10:00:00Z",
                "fecha_actualizacion": "2025-08-17T10:00:00Z"
            }
        }


class RutaCreateRequest(BaseModel):
    """Schema para la solicitud de creación de una ruta"""
    fecha: str = Field(..., min_length=10, max_length=10, description="Fecha de la ruta (YYYY-MM-DD)")
    bodega_origen: str = Field(..., min_length=1, description="Bodega de origen")
    estado: str = Field(..., min_length=1, description="Estado de la ruta")
    vehiculo_id: int = Field(..., description="ID del vehículo", gt=0)
    conductor_id: int = Field(..., description="ID del conductor", gt=0)
    condiciones_almacenamiento: Optional[str] = Field(None, description="Condiciones de almacenamiento")
    paradas: List[ParadaRequest] = Field(..., min_length=1, description="Lista de paradas")

    @field_validator('fecha')
    @classmethod
    def validate_fecha_format(cls, v: str) -> str:
        """Valida que la fecha tenga el formato correcto YYYY-MM-DD"""
        try:
            datetime.strptime(v, '%Y-%m-%d')
            return v
        except ValueError:
            raise ValueError('La fecha debe tener el formato YYYY-MM-DD')

    @field_validator('bodega_origen', 'estado')
    @classmethod
    def validate_not_empty(cls, v: str, info) -> str:
        """Valida que los campos no sean strings vacíos"""
        if not v or not v.strip():
            raise ValueError(f'{info.field_name} no puede estar vacío')
        return v.strip()

    class Config:
        json_schema_extra = {
            "example": {
                "fecha": "2025-08-17",
                "bodega_origen": "Central Bogotá",
                "estado": "Pendiente",
                "vehiculo_id": 12,
                "conductor_id": 4,
                "condiciones_almacenamiento": "Refrigerado",
                "paradas": [
                    {
                        "cliente_id": 32,
                        "direccion": "Calle 80 #45-20",
                        "contacto": "Carlos Ríos",
                        "latitud": 4.7110,
                        "longitud": -74.0721
                    },
                    {
                        "cliente_id": 15,
                        "direccion": "Av. 30 #22-10",
                        "contacto": "María López",
                        "latitud": 4.6097,
                        "longitud": -74.0817
                    }
                ]
            }
        }


class RutaCreateResponse(BaseModel):
    """Schema para la respuesta de creación de ruta"""
    id: int = Field(..., description="ID de la ruta creada")
    mensaje: str = Field(..., description="Mensaje de confirmación")

    class Config:
        json_schema_extra = {
            "example": {
                "id": 145,
                "mensaje": "Ruta creada exitosamente"
            }
        }


class RutaResponse(BaseModel):
    """Schema para la respuesta completa de una ruta"""
    id: int = Field(..., description="ID de la ruta")
    fecha: str = Field(..., description="Fecha de la ruta")
    bodega_origen: str = Field(..., description="Bodega de origen")
    estado: str = Field(..., description="Estado de la ruta")
    vehiculo_id: int = Field(..., description="ID del vehículo")
    conductor_id: int = Field(..., description="ID del conductor")
    vehiculo_placa: Optional[str] = Field(None, description="Placa del vehículo")
    vehiculo_info: Optional[str] = Field(None, description="Información del vehículo (marca y modelo)")
    conductor_nombre: Optional[str] = Field(None, description="Nombre completo del conductor")
    condiciones_almacenamiento: Optional[str] = Field(None, description="Condiciones de almacenamiento")
    fecha_creacion: datetime = Field(..., description="Fecha de creación")
    fecha_actualizacion: datetime = Field(..., description="Fecha de actualización")
    paradas: List[ParadaResponse] = Field(default_factory=list, description="Lista de paradas")

    class Config:
        json_schema_extra = {
            "example": {
                "id": 145,
                "fecha": "2025-08-17",
                "bodega_origen": "Central Bogotá",
                "estado": "Pendiente",
                "vehiculo_id": 12,
                "conductor_id": 4,
                "vehiculo_placa": "ABC123",
                "vehiculo_info": "Chevrolet NQR",
                "conductor_nombre": "Juan Pérez",
                "condiciones_almacenamiento": "Refrigerado",
                "fecha_creacion": "2025-08-17T10:00:00Z",
                "fecha_actualizacion": "2025-08-17T10:00:00Z",
                "paradas": [
                    {
                        "id": 1,
                        "ruta_id": 145,
                        "cliente_id": 32,
                        "direccion": "Calle 80 #45-20",
                        "contacto": "Carlos Ríos",
                        "latitud": 4.7110,
                        "longitud": -74.0721,
                        "orden": 1,
                        "estado": "Pendiente",
                        "fecha_creacion": "2025-08-17T10:00:00Z",
                        "fecha_actualizacion": "2025-08-17T10:00:00Z"
                    }
                ]
            }
        }


class RutasListResponse(BaseModel):
    """Schema para la respuesta de listado de rutas con paginación"""
    total: int = Field(..., description="Total de rutas")
    page: int = Field(..., description="Página actual")
    page_size: int = Field(..., description="Tamaño de página")
    total_pages: int = Field(..., description="Total de páginas")
    rutas: List[RutaResponse] = Field(..., description="Lista de rutas")

    class Config:
        json_schema_extra = {
            "example": {
                "total": 25,
                "page": 1,
                "page_size": 10,
                "total_pages": 3,
                "rutas": [
                    {
                        "id": 145,
                        "fecha": "2025-08-17",
                        "bodega_origen": "Central Bogotá",
                        "estado": "Pendiente",
                        "vehiculo_id": 12,
                        "conductor_id": 4,
                        "condiciones_almacenamiento": "Refrigerado",
                        "fecha_creacion": "2025-08-17T10:00:00Z",
                        "fecha_actualizacion": "2025-08-17T10:00:00Z",
                        "paradas": []
                    }
                ]
            }
        }

