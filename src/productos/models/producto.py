from sqlalchemy import Column, String, Integer, Numeric, Boolean, Text, DateTime, Index
from sqlalchemy.sql import func
from db.database import Base
import uuid
from datetime import datetime, timezone
import random
import string
from sqlalchemy.dialects.postgresql import UUID


class Producto(Base):
    __tablename__ = "productos"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    nombre = Column(String(255), nullable=False)
    descripcion = Column(Text, nullable=True)
    categoria = Column(String(100), nullable=False)
    imagen_url = Column(String(500), nullable=True)
    precio_unitario = Column(Numeric(10, 2), nullable=False)
    disponible = Column(Boolean, nullable=False, default=True)
    unidad_medida = Column(String(50), nullable=False, default="UNIDAD")
    sku = Column(String(100), nullable=False, unique=True)
    tipo_almacenamiento = Column(String(50), nullable=False, default="AMBIENTE")
    observaciones = Column(Text, nullable=True)
    proveedor_id = Column(UUID(as_uuid=True), nullable=False) 
    proveedor_nombre = Column(String(255), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    def __init__(
        self,
        nombre,
        descripcion,
        categoria,
        imagen_url,
        precio_unitario,
        disponible,
        unidad_medida,
        tipo_almacenamiento="AMBIENTE",
        observaciones=None,
        sku=None,
        proveedor_id=None,
        proveedor_nombre=None,
    ):
        self.nombre = nombre
        self.descripcion = descripcion
        self.categoria = categoria
        self.imagen_url = imagen_url
        self.precio_unitario = precio_unitario
        self.disponible = disponible
        self.unidad_medida = unidad_medida
        self.sku = sku or self._generate_sku()
        self.proveedor_id = proveedor_id
        self.proveedor_nombre = proveedor_nombre
        self.tipo_almacenamiento = tipo_almacenamiento
        self.observaciones = observaciones

    @staticmethod
    def _generate_sku():
        """Generate a unique SKU with format: PRD-YYYYMMDD-XXXXX"""
        date_part = datetime.now(timezone.utc).strftime("%Y%m%d")
        random_part = "".join(
            random.choices(string.ascii_uppercase + string.digits, k=5)
        )
        return f"PRD-{date_part}-{random_part}"

    def __repr__(self):
        return f"<Producto(id={self.id}, nombre={self.nombre}, categoria={self.categoria}, disponible={self.disponible})>"
    
    def to_dict(self):
        """
        Convierte el objeto SQLAlchemy en un dict.
        Este dict es usado por el servicio para construir las respuestas.
        """
        return {
            "id": self.id,
            "nombre": self.nombre,
            "descripcion": self.descripcion,
            "categoria": self.categoria,
            "imagen_url": self.imagen_url,
            "precio_unitario": str(self.precio_unitario),
            "disponible": self.disponible,
            "unidad_medida": self.unidad_medida,
            "tipo_almacenamiento": self.tipo_almacenamiento,
            "observaciones": self.observaciones,
            "sku": self.sku,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "proveedor_id": str(self.proveedor_id), 
            "proveedor_nombre": self.proveedor_nombre,
        }