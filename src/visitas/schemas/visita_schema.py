from datetime import datetime, date
from typing import Optional, Dict
from pydantic import BaseModel, UUID4, Field
from typing import List
import uuid

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
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True