from sqlalchemy import Column, String, DateTime
from sqlalchemy.dialects.postgresql import UUID
from datetime import datetime, timezone
import uuid
from db.database import Base


class ClienteInstitucional(Base):
    __tablename__ = "clientes_institucionales"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    fecha_creacion = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    fecha_actualizacion = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    
    nombre = Column(String(255), nullable=False)
    nit = Column(String(20), nullable=False, unique=True)
    logo_url = Column(String(500), nullable=True)
    address = Column(String(500), nullable=True)
    
    id_vendedor = Column(UUID(as_uuid=True), nullable=True, index=True)

    def __init__(self, nombre: str, nit: str, id_vendedor: str, address:str, logo_url: str = None):
        now = datetime.now(timezone.utc)
        self.id = uuid.uuid4()
        self.fecha_creacion = now
        self.fecha_actualizacion = now
        self.nombre = nombre
        self.nit = nit
        self.id_vendedor = uuid.UUID(id_vendedor) if isinstance(id_vendedor, str) else id_vendedor
        self.logo_url = logo_url
        self.address = address

    def to_dict(self):
        return {
            "id": str(self.id),
            "nombre": self.nombre,
            "nit": self.nit,
            "logoUrl": self.logo_url,
            "address": self.address,
            "fecha_creacion": self.fecha_creacion.isoformat() if self.fecha_creacion else None,
            "fecha_actualizacion": self.fecha_actualizacion.isoformat() if self.fecha_actualizacion else None,
            "id_vendedor": str(self.id_vendedor)
        }
