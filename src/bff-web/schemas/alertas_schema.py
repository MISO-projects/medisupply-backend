from pydantic import BaseModel, EmailStr, Field, UUID4
from typing import Optional, List, Dict, Any
from datetime import datetime


class AlertaBase(BaseModel):
    """Schema base para alertas"""
    id: UUID4
    tipo: str
    severidad: str
    mensaje: str
    estado: str
    created_at: datetime

    class Config:
        from_attributes = True


class AlertaDetalleResponse(AlertaBase):
    """Schema con detalle completo de una alerta"""
    descripcion_detallada: Optional[str]
    evento_relacionado: Optional[Dict[str, Any]]
    audit_log_id: Optional[UUID4]
    revisado_por: Optional[UUID4]
    notas_revision: Optional[str]
    notificacion_enviada: bool
    updated_at: Optional[datetime]

    class Config:
        from_attributes = True


class AlertasListResponse(BaseModel):
    """Schema para lista paginada de alertas"""
    items: List[AlertaDetalleResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


class RevisarAlertaRequest(BaseModel):
    """Schema para revisar una alerta"""
    estado: str = Field(..., description="Nuevo estado: REVISADO, RESUELTO, FALSA_ALARMA")
    revisado_por: Optional[UUID4] = Field(None, description="UUID del usuario que revisa")
    notas_revision: Optional[str] = Field(None, description="Notas sobre la revisión")


class EstadisticasAlertasResponse(BaseModel):
    """Schema para estadísticas de alertas"""
    total_alertas: int
    por_severidad: Dict[str, int]
    por_estado: Dict[str, int]
    por_tipo: Dict[str, int]
    alertas_ultimas_24h: int
    alertas_pendientes: int


class EmailNotificacionResponse(BaseModel):
    """Schema de respuesta para email de notificación"""
    id: UUID4
    email: EmailStr
    nombre: Optional[str]
    cargo: Optional[str]
    activo: bool
    severidades_minimas: List[str]
    created_at: datetime
    updated_at: Optional[datetime]

    class Config:
        from_attributes = True


class RegistrarEmailRequest(BaseModel):
    """Schema para registrar un email"""
    email: EmailStr = Field(..., description="Email del destinatario")
    nombre: Optional[str] = Field(None, max_length=255, description="Nombre del destinatario")
    cargo: Optional[str] = Field(None, max_length=100, description="Cargo del destinatario")
    severidades_minimas: List[str] = Field(
        default=["ALTA", "CRITICA"],
        description="Severidades que recibirá"
    )






