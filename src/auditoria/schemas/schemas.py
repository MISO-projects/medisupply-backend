from pydantic import BaseModel, EmailStr, Field, UUID4
from typing import Optional, List, Dict, Any
from datetime import datetime


class EventoInventarioSchema(BaseModel):
    """Schema para eventos de inventario recibidos desde Pub/Sub"""
    event_type: str
    operation: str
    timestamp: str
    inventario_id: Optional[str] = None
    producto_id: Optional[str] = None
    usuario_id: Optional[str] = None
    ip_origen: Optional[str] = None
    datos: Optional[Dict[str, Any]] = None
    cambios: Optional[Dict[str, Any]] = None

    class Config:
        from_attributes = True


class RegistrarEmailSchema(BaseModel):
    """Schema para registrar un email para notificaciones"""
    email: EmailStr = Field(..., description="Email del destinatario")
    nombre: Optional[str] = Field(None, max_length=255, description="Nombre del destinatario")
    cargo: Optional[str] = Field(None, max_length=100, description="Cargo o rol del destinatario")
    severidades_minimas: List[str] = Field(
        default=["ALTA", "CRITICA"],
        description="Lista de severidades que recibirá (BAJA, MEDIA, ALTA, CRITICA)"
    )

    class Config:
        from_attributes = True


class EmailNotificacionResponseSchema(RegistrarEmailSchema):
    """Schema de respuesta para email de notificación"""
    id: UUID4
    activo: bool
    created_at: datetime
    updated_at: Optional[datetime]

    class Config:
        from_attributes = True


class ActualizarEmailSchema(BaseModel):
    """Schema para actualizar configuración de email"""
    nombre: Optional[str] = Field(None, max_length=255)
    cargo: Optional[str] = Field(None, max_length=100)
    activo: Optional[bool] = None
    severidades_minimas: Optional[List[str]] = None

    class Config:
        from_attributes = True


class AlertaResponseSchema(BaseModel):
    """Schema de respuesta para alertas"""
    id: UUID4
    tipo: str
    severidad: str
    mensaje: str
    descripcion_detallada: Optional[str]
    evento_relacionado: Optional[Dict[str, Any]]
    audit_log_id: Optional[UUID4]
    estado: str
    revisado_por: Optional[UUID4]
    notas_revision: Optional[str]
    notificacion_enviada: bool
    created_at: datetime
    updated_at: Optional[datetime]

    class Config:
        from_attributes = True


class AlertasListResponse(BaseModel):
    """Schema para lista paginada de alertas"""
    items: List[AlertaResponseSchema]
    total: int
    page: int
    page_size: int
    total_pages: int


class RevisarAlertaSchema(BaseModel):
    """Schema para revisar/actualizar una alerta"""
    estado: str = Field(..., description="Nuevo estado: REVISADO, RESUELTO, FALSA_ALARMA")
    revisado_por: Optional[UUID4] = Field(None, description="UUID del usuario que revisa")
    notas_revision: Optional[str] = Field(None, description="Notas sobre la revisión")

    class Config:
        from_attributes = True


class EstadisticasAlertasResponse(BaseModel):
    """Schema para estadísticas de alertas"""
    total_alertas: int
    por_severidad: Dict[str, int]
    por_estado: Dict[str, int]
    por_tipo: Dict[str, int]
    alertas_ultimas_24h: int
    alertas_pendientes: int







