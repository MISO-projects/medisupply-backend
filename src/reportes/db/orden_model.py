from sqlalchemy import Column, DateTime, Integer, String, Numeric, Text
from sqlalchemy.dialects.postgresql import UUID
from .database import Base


class OrderProjection(Base):
    """
    Modelo de solo lectura para la tabla order_projections.
    Usado en reportes para obtener información de órdenes.
    """
    __tablename__ = "order_projections"

    id = Column(UUID(as_uuid=True), primary_key=True)
    numero_orden = Column(String, nullable=False, index=True)
    fecha_creacion = Column(DateTime, nullable=False, index=True)
    fecha_actualizacion = Column(DateTime, nullable=False)
    fecha_entrega_estimada = Column(DateTime, nullable=False)
    estado = Column(String, nullable=False, index=True)
    valor_total = Column(Numeric, nullable=False)
    id_cliente = Column(UUID(as_uuid=True), nullable=False, index=True)
    id_vendedor = Column(UUID(as_uuid=True), nullable=False, index=True)
    creado_por = Column(UUID(as_uuid=True), nullable=False)
    detalles = Column(Text, nullable=False)
    cantidad_items = Column(Integer, nullable=False)
    observaciones = Column(String)
    version = Column(Integer, default=1)
    processed_at = Column(DateTime)
