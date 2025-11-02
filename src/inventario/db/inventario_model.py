from sqlalchemy import Column, String, Integer, DateTime, Text, Date, ForeignKey
# from pydantic import BaseModel, Field, field_validator
from sqlalchemy.sql import func
# from sqlalchemy.orm import relationship
from db.database import Base # Asumo que Base está en db.database
import uuid
from datetime import datetime
from sqlalchemy.dialects.postgresql import UUID

# Nota: Asegúrate de importar Date si quieres que fecha_vencimiento sea solo la fecha sin hora.
# Si estás usando solo DateTime en la base de datos (con timezone=True), puedes mantener DateTime.
# Basado en tu CREATE TABLE original (DATE), he usado Date aquí.

class Inventario(Base):
    __tablename__ = "inventario"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    producto_id = Column(UUID(as_uuid=True), nullable=False) 
    lote = Column(String(100), nullable=False, default="LT-UNDEFINED")
    fecha_vencimiento = Column(Date, nullable=True)
    cantidad = Column(Integer, nullable=False, default=0)
    ubicacion = Column(String(100), nullable=False, default="BODEGA-PRINCIPAL")
    temperatura_requerida = Column(String(50), nullable=False, default="AMBIENTE")
    estado = Column(String(50), nullable=False, default="DISPONIBLE") #(AGOTADO, RESERVADO, DAÑADO). 
    condiciones_especiales = Column(Text, nullable=True)
    observaciones = Column(Text, nullable=True)
    fecha_recepcion = Column(DateTime(timezone=True), server_default=func.now())
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now()) 

    # --- Relaciones (Opcional, pero buena práctica) ---
    # producto = relationship("Producto", back_populates="inventario_registros")

    # Constructor optimizado
    def __init__(
        self,
        producto_id: uuid.UUID,
        lote: str,
        fecha_vencimiento: datetime.date, 
        cantidad: int,
        ubicacion: str = "BODEGA-PRINCIPAL",
        temperatura_requerida: str = "AMBIENTE",
        estado: str = "DISPONIBLE",
        condiciones_especiales: str = None,
        observaciones: str = None,
    ):
        self.producto_id = producto_id
        self.lote = lote
        self.fecha_vencimiento = fecha_vencimiento
        self.cantidad = cantidad
        self.ubicacion = ubicacion
        self.temperatura_requerida = temperatura_requerida
        self.estado = estado
        self.condiciones_especiales = condiciones_especiales
        self.observaciones = observaciones   

    def to_dict(self):
        return {
            "id": str(self.id),
            "producto_id": str(self.producto_id),
            "lote": self.lote,
            "fecha_recepcion": self.fecha_recepcion.isoformat() if self.fecha_recepcion else None,
            "fecha_vencimiento": self.fecha_vencimiento.isoformat() if self.fecha_vencimiento else None,
            "cantidad": self.cantidad,
            "ubicacion": self.ubicacion,
            "temperatura_requerida": self.temperatura_requerida,
            "estado": self.estado,
            "condiciones_especiales": self.condiciones_especiales,
            "observaciones": self.observaciones,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
    
    # class InventarioListResponse(BaseModel):
    # total: int
    # page: int
    # page_size: int
    # total_pages: int
    # inventario: list[InventarioConDetalle]

 