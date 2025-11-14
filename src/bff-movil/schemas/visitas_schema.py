from datetime import datetime, date
from typing import Optional, Dict
from pydantic import BaseModel, UUID4, Field
from typing import List
import uuid
from enum import Enum

class EstadoVisitaEnum(str, Enum):
    """Define los estados permitidos para una visita."""
    PENDIENTE = "PENDIENTE"
    REALIZADA = "REALIZADA"
    CANCELADA = "CANCELADA"

class NotaVisitaAnteriorSchema(BaseModel):
    fecha_visita_programada: datetime
    detalle: Optional[str] = None

    class Config:
        from_attributes = True

class CrearRutaVisitaSchema(BaseModel):
    """Esquema de datos requeridos para crear una nueva ruta de visita."""
    cliente_id: UUID4 = Field(..., description="UUID del cliente a visitar.")

    class Config:
        from_attributes = True


class VisitaResponseSchema(BaseModel):
    """Esquema de respuesta para una visita creada o consultada."""
    id: UUID4
    cliente_id: UUID4
    cliente_contacto: Optional[str] = None
    fecha_visita_programada: datetime
    vendedor_id: UUID4
    detalle: Optional[str] = None
    evidencia: Optional[str] = None
    inicio: Optional[datetime] = None
    fin: Optional[datetime] = None
    estado: str
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class RutaVisitaItemSchema(BaseModel):
    """
    Schema simplificado para la lista de rutas de visita, 
    diseñado para la vista móvil.
    """
    id: UUID4 = Field(..., description="ID único de la visita (para navegar al detalle)")
    cliente_id: UUID4 = Field(..., description="ID del cliente")
    nombre: str = Field(..., description="Nombre del cliente institucional")
    direccion: Optional[str] = Field(None, description="Dirección del cliente")
    hora_de_la_cita: str = Field(..., description="Hora de la visita en formato HH:MM (ej: '08:50')")
    estado: Optional[EstadoVisitaEnum] = Field(None, description="Nuevo estado de la visita (PENDIENTE, RELIZADA, CANCELADA)")

    class Config:
        from_attributes = True

class VisitaDetalleResponseSchema(VisitaResponseSchema):
    """
    Schema de respuesta con toda la información de una visita,
    enriquecida con detalles del cliente.
    Hereda todos los campos de VisitaBaseResponseSchema.
    """
    nombre_institucion: str = Field(..., description="Nombre del cliente institucional")
    direccion: Optional[str] = Field(None, description="Dirección del cliente")
    notas_visitas_anteriores: List[NotaVisitaAnteriorSchema] = Field(
        default_factory=list, 
        description="Lista de notas de visitas pasadas del mismo cliente."
    )

    class Config:
        from_attributes = True

class ActualizarVisitaSchema(BaseModel):
    """Schema para actualizar una visita (campos opcionales)."""
    inicio: Optional[datetime] = Field(None, description="Hora y fecha de inicio real de la visita")
    fin: Optional[datetime] = Field(None, description="Hora y fecha de fin real de la visita")
    cliente_contacto: Optional[str] = Field(None, max_length=100, description="Nombre del contacto en el cliente")
    detalle: Optional[str] = Field(None, max_length=100, description="Detalles o notas de la visita")
    evidencia: Optional[str] = Field(None, max_length=100, description="URL de la foto o video de evidencia")
    estado: Optional[EstadoVisitaEnum] = Field(None, description="Nuevo estado de la visita (PENDIENTE, REALIZADA, CANCELADA)")

    class Config:
        from_attributes = True