from sqlalchemy import Column, String, DateTime, Integer, Numeric, Text
from sqlalchemy.dialects.postgresql import UUID
from .database import Base


class OrderProjection(Base):
    """
    Modelo de solo lectura para la tabla order_projections.
    Usado para obtener información de los pedidos asociados a paradas.
    """
    __tablename__ = "order_projections"

    id = Column(UUID(as_uuid=True), primary_key=True)
    numero_orden = Column(String, nullable=False)
    fecha_creacion = Column(DateTime, nullable=False)
    fecha_actualizacion = Column(DateTime, nullable=False)
    fecha_entrega_estimada = Column(DateTime, nullable=False)
    estado = Column(String, nullable=False)
    valor_total = Column(Numeric, nullable=False)
    id_cliente = Column(UUID(as_uuid=True), nullable=False)
    id_vendedor = Column(UUID(as_uuid=True), nullable=False)
    creado_por = Column(UUID(as_uuid=True), nullable=False)
    detalles = Column(Text, nullable=False)
    cantidad_items = Column(Integer, nullable=False)
    observaciones = Column(String, nullable=True)
    version = Column(Integer, default=1)
    processed_at = Column(DateTime)
    id_bodega_origen = Column(UUID(as_uuid=True), nullable=True)


class ClienteInstitucional(Base):
    """
    Modelo de solo lectura para la tabla clientes_institucionales.
    Usado para obtener el nombre del cliente.
    """
    __tablename__ = "clientes_institucionales"

    id = Column(UUID(as_uuid=True), primary_key=True)
    fecha_creacion = Column(DateTime)
    fecha_actualizacion = Column(DateTime)
    nombre = Column(String(255), nullable=False)
    nit = Column(String(20), nullable=False)
    logo_url = Column(String(500))
    address = Column(String(500))
    id_vendedor = Column(UUID(as_uuid=True))

