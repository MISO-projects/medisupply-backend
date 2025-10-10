from sqlalchemy import Column, DateTime, String, Numeric
from sqlalchemy.dialects.postgresql import UUID
from datetime import datetime, timezone
import uuid
from .database import Base


class Vendedor(Base):
    __tablename__ = "vendedores"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    fecha_creacion = Column(DateTime, default=datetime.now)
    fecha_actualizacion = Column(DateTime, default=datetime.now)
    nombre = Column(String(255), nullable=False)
    documento_identidad = Column(String, nullable=True)
    email = Column(String, nullable=False, unique=True)
    zona_asignada = Column(String, nullable=False)
    plan_venta = Column(String, nullable=False)
    meta_venta = Column(Numeric(12, 2), nullable=True)

    def __init__(self, nombre, documento_identidad, email, zona_asignada, plan_venta=None, meta_venta=None):
        now = datetime.now(timezone.utc)
        self.fecha_creacion = now
        self.fecha_actualizacion = now
        self.nombre = nombre
        self.documento_identidad = documento_identidad
        self.email = email
        self.zona_asignada = zona_asignada
        self.plan_venta = plan_venta
        self.meta_venta = meta_venta

    def to_dict(self):
        """Convert Vendedor instance to dictionary"""
        return {
            "id": str(self.id),
            "fecha_creacion": self.fecha_creacion.isoformat() if self.fecha_creacion else None,
            "fecha_actualizacion": self.fecha_actualizacion.isoformat() if self.fecha_actualizacion else None,
            "nombre": self.nombre,
            "documento_identidad": self.documento_identidad,
            "email": self.email,
            "zona_asignada": self.zona_asignada,
            "plan_venta": self.plan_venta,
            "meta_venta": str(self.meta_venta) if self.meta_venta else None,
        }
