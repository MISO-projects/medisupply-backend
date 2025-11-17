from sqlalchemy import Column, String, DateTime
from sqlalchemy.dialects.postgresql import UUID
from .database import Base


class Vendedor(Base):
    """
    Modelo de solo lectura para la tabla vendedores.
    Usado en reportes para obtener información de vendedores.
    """
    __tablename__ = "vendedores"

    id = Column(UUID(as_uuid=True), primary_key=True)
    fecha_creacion = Column(DateTime)
    fecha_actualizacion = Column(DateTime)
    nombre = Column(String(255), nullable=False)
    documento_identidad = Column(String)
    email = Column(String, nullable=False)
    zona_asignada = Column(String, nullable=False)
    plan_venta_id = Column(UUID(as_uuid=True))
