from sqlalchemy import Column, String, Integer, DateTime, Text, Date, ForeignKey
# from pydantic import BaseModel, Field, field_validator
from sqlalchemy.sql import func
# from sqlalchemy.orm import relationship
from db.database import Base 
import uuid
from datetime import datetime
from sqlalchemy.dialects.postgresql import UUID


class Visita(Base):
    __tablename__ = "visitas"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    cliente_id = Column(UUID(as_uuid=True), nullable=False) 
    cliente_contacto = Column(String(100), nullable=False)
    vendedor_id = Column(UUID(as_uuid=True), nullable=False) 
    detalle = Column(String(100), nullable=False)
    evidencia = Column(String(100), nullable=False)
    inicio =  Column(DateTime(timezone=True), server_default=func.now())
    fin = Column(DateTime(timezone=True), server_default=func.now())
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now()) 

    def __init__(
        self,
        cliente_id: uuid.UUID,
        cliente_contacto: str,
        vendedor_id: uuid.UUID,
        detalle: str, 
        evidencia: str,
        inicio: datetime,
        fin: datetime
    ):
        """
        Constructor para crear una instancia de Visita.
        'id', 'created_at' y 'updated_at' se manejan automáticamente
        por la base de datos o SQLAlchemy.
        """
        self.cliente_id = cliente_id
        self.cliente_contacto = cliente_contacto
        self.vendedor_id = vendedor_id
        self.detalle = detalle
        self.evidencia = evidencia
        self.inicio = inicio
        self.fin = fin

    def to_dict(self):
        """
        Convierte el objeto Visita a un diccionario serializable.
        """
        return {
            "id": str(self.id),
            "cliente_id": str(self.cliente_id),
            "cliente_contacto": self.cliente_contacto,
            "vendedor_id": str(self.vendedor_id),
            "detalle": self.detalle,
            "evidencia": self.evidencia,
            "inicio": self.inicio.isoformat() if self.inicio else None,
            "fin": self.fin.isoformat() if self.fin else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }