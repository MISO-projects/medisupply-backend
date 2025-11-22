from sqlalchemy import Column, String, DateTime
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.sql import func
from db.database import Base
import uuid
from datetime import datetime

class AuditLog(Base):
    """Registro de auditoría de operaciones de inventario (Modelo Local en Inventario)"""
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

