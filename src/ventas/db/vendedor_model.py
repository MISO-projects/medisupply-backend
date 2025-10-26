from sqlalchemy import Column, DateTime, String, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
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
    plan_venta_id = Column(UUID(as_uuid=True), ForeignKey('planes_venta.id'), nullable=False)

    # Relación con PlanVenta
    plan_venta = relationship("PlanVenta", foreign_keys=[plan_venta_id])

    def __init__(self, nombre, documento_identidad, email, zona_asignada, plan_venta_id):
        now = datetime.now(timezone.utc)
        self.fecha_creacion = now
        self.fecha_actualizacion = now
        self.nombre = nombre
        self.documento_identidad = documento_identidad
        self.email = email
        self.zona_asignada = zona_asignada
        self.plan_venta_id = plan_venta_id

    def to_dict(self, include_plan_venta=False):
        """
        Convert Vendedor instance to dictionary

        Args:
            include_plan_venta: Si es True, incluye información expandida del plan de venta
        """
        result = {
            "id": str(self.id),
            "fecha_creacion": self.fecha_creacion.isoformat() if self.fecha_creacion else None,
            "fecha_actualizacion": self.fecha_actualizacion.isoformat() if self.fecha_actualizacion else None,
            "nombre": self.nombre,
            "documento_identidad": self.documento_identidad,
            "email": self.email,
            "zona_asignada": self.zona_asignada,
            "plan_venta_id": str(self.plan_venta_id),
        }

        # Incluir información del plan de venta si se solicita
        if include_plan_venta and self.plan_venta:
            result["plan_venta"] = {
                "id": str(self.plan_venta.id),
                "nombre": self.plan_venta.nombre,
                "fecha_inicio": self.plan_venta.fecha_inicio.isoformat() if self.plan_venta.fecha_inicio else None,
                "fecha_fin": self.plan_venta.fecha_fin.isoformat() if self.plan_venta.fecha_fin else None,
                "meta_venta": str(self.plan_venta.meta_venta) if self.plan_venta.meta_venta else None,
                "zona_asignada": self.plan_venta.zona_asignada,
            }

        return result
