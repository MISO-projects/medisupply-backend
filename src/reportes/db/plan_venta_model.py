from sqlalchemy import Column, DateTime, String, Numeric, Text
from sqlalchemy.dialects.postgresql import UUID
from .database import Base


class PlanVenta(Base):
    """
    Modelo de solo lectura para la tabla planes_venta.
    Usado en reportes para obtener información de planes de venta.
    """
    __tablename__ = "planes_venta"

    id = Column(UUID(as_uuid=True), primary_key=True)
    fecha_creacion = Column(DateTime)
    fecha_actualizacion = Column(DateTime)
    nombre = Column(String(255), nullable=False)
    fecha_inicio = Column(DateTime, nullable=False)
    fecha_fin = Column(DateTime, nullable=False)
    descripcion = Column(Text)
    meta_venta = Column(Numeric(12, 2), nullable=False)
    zona_asignada = Column(String)
