from sqlalchemy import Column, String, Integer, Numeric, Boolean, Text, DateTime
from sqlalchemy.sql import func
from db.database import Base
import uuid


class Producto(Base):
    __tablename__ = "productos"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    nombre = Column(String(255), nullable=False)
    descripcion = Column(Text, nullable=True)
    categoria = Column(String(100), nullable=False)
    imagen_url = Column(String(500), nullable=True)
    precio_unitario = Column(Numeric(10, 2), nullable=False)
    stock_disponible = Column(Integer, nullable=False, default=0)
    disponible = Column(Boolean, nullable=False, default=True)
    unidad_medida = Column(String(50), nullable=False, default='UNIDAD')
    sku = Column(String(100), nullable=True, unique=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    def __repr__(self):
        return f"<Producto(id={self.id}, nombre={self.nombre}, categoria={self.categoria}, stock={self.stock_disponible})>"

