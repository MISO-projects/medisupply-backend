from sqlalchemy import Column, String, DateTime
from sqlalchemy.dialects.postgresql import UUID
from .database import Base


class ClienteInstitucional(Base):
    """
    Modelo de solo lectura para la tabla clientes_institucionales.
    Usado para hacer JOIN con order_projections y obtener el nombre del cliente.
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

