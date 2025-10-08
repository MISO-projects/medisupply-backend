from sqlalchemy import Column, DateTime, String
from sqlalchemy.dialects.postgresql import UUID
from datetime import datetime, timezone
import uuid
from .database import Base


class Proveedor(Base):
    __tablename__ = "proveedores"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    fecha_creacion = Column(DateTime, default=datetime.now())
    fecha_actualizacion = Column(DateTime, default=datetime.now())
    nombre = Column(String(255), nullable=False)
    id_tributario = Column(String, nullable=False, unique=True)
    tipo_proveedor = Column(String, nullable=False)
    email = Column(String, nullable=False, unique=True)
    pais = Column(String, nullable=False)
    contacto = Column(String(255), nullable=True)
    condiciones_entrega = Column(String(500), nullable=True)

    def __init__(self, nombre, id_tributario, tipo_proveedor, email, pais, contacto=None, condiciones_entrega=None):
        now = datetime.now(timezone.utc)
        self.fecha_creacion = now
        self.fecha_actualizacion = now
        self.nombre = nombre
        self.id_tributario = id_tributario
        self.tipo_proveedor = tipo_proveedor
        self.email = email
        self.pais = pais
        self.contacto = contacto
        self.condiciones_entrega = condiciones_entrega

    def to_dict(self):
        """Convert Proveedor instance to dictionary"""
        return {
            "id": str(self.id),
            "fecha_creacion": self.fecha_creacion.isoformat() if self.fecha_creacion else None,
            "fecha_actualizacion": self.fecha_actualizacion.isoformat() if self.fecha_actualizacion else None,
            "nombre": self.nombre,
            "id_tributario": self.id_tributario,
            "tipo_proveedor": self.tipo_proveedor,
            "email": self.email,
            "pais": self.pais,
            "contacto": self.contacto,
            "condiciones_entrega": self.condiciones_entrega,
        }
