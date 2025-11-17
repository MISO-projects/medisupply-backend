from sqlalchemy import Column, String, Integer, DateTime, Text, Boolean
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.sql import func
from db.database import Base
import uuid
from datetime import datetime


class AuditLog(Base):
    """Registro de auditoría de operaciones de inventario"""
    __tablename__ = "audit_log"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    event_type = Column(String(50), nullable=False, index=True)
    operation = Column(String(50), nullable=False, index=True)
    inventario_id = Column(UUID(as_uuid=True), nullable=True, index=True)
    producto_id = Column(UUID(as_uuid=True), nullable=True, index=True)
    usuario_id = Column(UUID(as_uuid=True), nullable=True, index=True)
    ip_origen = Column(String(45), nullable=True)
    datos_operacion = Column(JSONB, nullable=True)
    cambios = Column(JSONB, nullable=True)
    timestamp = Column(DateTime(timezone=True), nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    def to_dict(self):
        return {
            "id": str(self.id),
            "event_type": self.event_type,
            "operation": self.operation,
            "inventario_id": str(self.inventario_id) if self.inventario_id else None,
            "producto_id": str(self.producto_id) if self.producto_id else None,
            "usuario_id": str(self.usuario_id) if self.usuario_id else None,
            "ip_origen": self.ip_origen,
            "datos_operacion": self.datos_operacion,
            "cambios": self.cambios,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class Alerta(Base):
    """Alertas de seguridad generadas por patrones sospechosos"""
    __tablename__ = "alertas"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tipo = Column(String(100), nullable=False, index=True)
    severidad = Column(String(20), nullable=False, index=True)  # BAJA, MEDIA, ALTA, CRITICA
    mensaje = Column(Text, nullable=False)
    descripcion_detallada = Column(Text, nullable=True)
    evento_relacionado = Column(JSONB, nullable=True)
    audit_log_id = Column(UUID(as_uuid=True), nullable=True)
    estado = Column(String(20), default="PENDIENTE", index=True)  # PENDIENTE, REVISADO, RESUELTO, FALSA_ALARMA
    revisado_por = Column(UUID(as_uuid=True), nullable=True)
    notas_revision = Column(Text, nullable=True)
    notificacion_enviada = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    def to_dict(self):
        return {
            "id": str(self.id),
            "tipo": self.tipo,
            "severidad": self.severidad,
            "mensaje": self.mensaje,
            "descripcion_detallada": self.descripcion_detallada,
            "evento_relacionado": self.evento_relacionado,
            "audit_log_id": str(self.audit_log_id) if self.audit_log_id else None,
            "estado": self.estado,
            "revisado_por": str(self.revisado_por) if self.revisado_por else None,
            "notas_revision": self.notas_revision,
            "notificacion_enviada": self.notificacion_enviada,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class EmailNotificacion(Base):
    """Emails registrados para recibir notificaciones de alertas"""
    __tablename__ = "email_notificaciones"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String(255), nullable=False, unique=True, index=True)
    nombre = Column(String(255), nullable=True)
    cargo = Column(String(100), nullable=True)
    activo = Column(Boolean, default=True, index=True)
    severidades_minimas = Column(JSONB, default=["ALTA", "CRITICA"])  # Solo recibe estas severidades o superiores
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    def to_dict(self):
        return {
            "id": str(self.id),
            "email": self.email,
            "nombre": self.nombre,
            "cargo": self.cargo,
            "activo": self.activo,
            "severidades_minimas": self.severidades_minimas,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }







