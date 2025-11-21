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
    fecha_visita_programada: Optional[date] = Field(
        None, 
        description="Fecha opcional para la visita (YYYY-MM-DD). Si es None, se usa la lógica de hoy/próximo día hábil."
    )

    class Config:
        from_attributes = True

class ProductoPreferidoSchema(BaseModel):
    id_producto: str
    nombre: str
    cantidad_total: int


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
    cliente_contacto: Optional[str] = Field(None, description="Nombre del contacto en el cliente")
    notas_visitas_anteriores: List[NotaVisitaAnteriorSchema] = Field(
        default_factory=list, 
        description="Lista de notas de visitas pasadas del mismo cliente."
    )
    productos_preferidos: List[ProductoPreferidoSchema] = Field(
        default_factory=list,
        description="Ranking de productos más pedidos por este cliente."
    )
    tiempo_desplazamiento: Optional[str] = Field(
        None, 
        description="Tiempo de viaje estimado desde la ubicación actual del vendedor (ej: '15 min')."
    )

    class Config:
        from_attributes = True