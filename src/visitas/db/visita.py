from sqlalchemy import Column, String, Integer, DateTime, Text, Date, ForeignKey
from sqlalchemy.sql import func
from db.database import Base 
import uuid
from datetime import datetime
from sqlalchemy.dialects.postgresql import UUID
from typing import Optional 

class Visita(Base):
    __tablename__ = "visitas"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    cliente_id = Column(UUID(as_uuid=True), nullable=False)
    cliente_contacto = Column(String(100), nullable=True)
    fecha_visita_programada =  Column(DateTime(timezone=True), nullable=False)
    vendedor_id = Column(UUID(as_uuid=True), nullable=False) 
    detalle = Column(String(100), nullable=True)
    evidencia = Column(String(100), nullable=True)
    inicio =  Column(DateTime(timezone=True), nullable=True) 
    fin = Column(DateTime(timezone=True), nullable=True)
    estado = Column(String(50), nullable=False, default='PENDIENTE')
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now()) 

    def __init__(
        self,
        cliente_id: uuid.UUID,
        vendedor_id: uuid.UUID,
        fecha_visita_programada: datetime,
        cliente_contacto: Optional[str] = None, 
        detalle: Optional[str] = None,          
        evidencia: Optional[str] = None,        
        inicio: Optional[datetime] = None,      
        fin: Optional[datetime] = None,
        estado: Optional[str] = 'PENDIENTE'          
    ):
        """
        Constructor para crear una instancia de Visita.
        'id', 'created_at' y 'updated_at' se manejan automáticamente
        por la base de datos o SQLAlchemy.
        """
        self.cliente_id = cliente_id
        self.vendedor_id = vendedor_id
        self.fecha_visita_programada = fecha_visita_programada
        self.cliente_contacto = cliente_contacto
        self.detalle = detalle
        self.evidencia = evidencia
        self.inicio = inicio
        self.fin = fin
        self.estado = estado

    def to_dict(self):
        """
        Convierte el objeto Visita a un diccionario serializable.
        """
        return {
            "id": str(self.id),
            "cliente_id": str(self.cliente_id),
            "cliente_contacto": self.cliente_contacto,
            "fecha_visita_programada": self.fecha_visita_programada.isoformat() if self.fecha_visita_programada else None,
            "vendedor_id": str(self.vendedor_id),
            "detalle": self.detalle,
            "evidencia": self.evidencia,
            "inicio": self.inicio.isoformat() if self.inicio else None,
            "fin": self.fin.isoformat() if self.fin else None,
            "estado": self.estado,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }