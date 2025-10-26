from sqlalchemy import Column, DateTime, String, Numeric, Text
from sqlalchemy.dialects.postgresql import UUID
from datetime import datetime, timezone
import uuid
from .database import Base


class PlanVenta(Base):
    """
    Modelo de Plan de Venta.

    Un plan de venta define objetivos y metas comerciales para vendedores
    en períodos específicos y zonas geográficas determinadas.

    Attributes:
        id: Identificador único UUID
        fecha_creacion: Timestamp de creación del registro
        fecha_actualizacion: Timestamp de última actualización
        nombre: Nombre descriptivo del plan
        fecha_inicio: Fecha de inicio del plan
        fecha_fin: Fecha de finalización del plan
        descripcion: Descripción detallada opcional (texto largo)
        meta_venta: Meta monetaria del plan (Decimal con 2 decimales)
        zona_asignada: Zona geográfica asignada (opcional)
    """
    __tablename__ = "planes_venta"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    fecha_creacion = Column(DateTime, default=datetime.now)
    fecha_actualizacion = Column(DateTime, default=datetime.now)
    nombre = Column(String(255), nullable=False, unique=True)
    fecha_inicio = Column(DateTime, nullable=False)
    fecha_fin = Column(DateTime, nullable=False)
    descripcion = Column(Text, nullable=True)
    meta_venta = Column(Numeric(12, 2), nullable=False)
    zona_asignada = Column(String, nullable=True)

    def __init__(
        self,
        nombre,
        fecha_inicio,
        fecha_fin,
        meta_venta,
        descripcion=None,
        zona_asignada=None
    ):
        """
        Inicializa un nuevo Plan de Venta.

        Args:
            nombre: Nombre del plan
            fecha_inicio: Fecha de inicio del plan
            fecha_fin: Fecha de finalización del plan
            meta_venta: Meta monetaria a alcanzar
            descripcion: Descripción opcional del plan
            zona_asignada: Zona geográfica opcional
        """
        now = datetime.now(timezone.utc)
        self.fecha_creacion = now
        self.fecha_actualizacion = now
        self.nombre = nombre
        self.fecha_inicio = fecha_inicio
        self.fecha_fin = fecha_fin
        self.descripcion = descripcion
        self.meta_venta = meta_venta
        self.zona_asignada = zona_asignada

    def to_dict(self):
        """
        Convierte la instancia de PlanVenta a diccionario.

        Returns:
            Dict con todos los campos del plan de venta
        """
        return {
            "id": str(self.id),
            "fecha_creacion": self.fecha_creacion.isoformat() if self.fecha_creacion else None,
            "fecha_actualizacion": self.fecha_actualizacion.isoformat() if self.fecha_actualizacion else None,
            "nombre": self.nombre,
            "fecha_inicio": self.fecha_inicio.isoformat() if self.fecha_inicio else None,
            "fecha_fin": self.fecha_fin.isoformat() if self.fecha_fin else None,
            "descripcion": self.descripcion,
            "meta_venta": str(self.meta_venta) if self.meta_venta else None,
            "zona_asignada": self.zona_asignada,
        }
