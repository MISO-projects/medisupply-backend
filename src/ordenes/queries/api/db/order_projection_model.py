from sqlalchemy import Column, DateTime, Integer, String, Numeric, Text
from datetime import datetime
import uuid
from decimal import Decimal
from sqlalchemy.dialects.postgresql import UUID
import json
from .database import Base


class OrderProjection(Base):
    __tablename__ = "order_projections"

    id = Column(UUID(as_uuid=True), primary_key=True)
    numero_orden = Column(String, nullable=False, unique=True, index=True)

    fecha_creacion = Column(DateTime, nullable=False, index=True)
    fecha_actualizacion = Column(DateTime, nullable=False)
    fecha_entrega_estimada = Column(DateTime, nullable=False, index=True)
    estado = Column(String, nullable=False, index=True)
    valor_total = Column(Numeric, nullable=False)
    id_cliente = Column(UUID(as_uuid=True), nullable=False, index=True)
    id_vendedor = Column(UUID(as_uuid=True), nullable=False, index=True)
    id_bodega_origen = Column(UUID(as_uuid=True), nullable=False, index=True)
    creado_por = Column(UUID(as_uuid=True), nullable=False)
    detalles = Column(Text, nullable=False)
    cantidad_items = Column(Integer, nullable=False)
    observaciones = Column(String, nullable=True)

    version = Column(Integer, default=1)
    processed_at = Column(DateTime, default=datetime.utcnow)

    def __init__(self, order_data: dict):
        self.id = uuid.UUID(order_data.get('id'))
        self.numero_orden = order_data.get('numero_orden')
        self.fecha_creacion = order_data.get('fecha_creacion')
        self.fecha_actualizacion = order_data.get('fecha_actualizacion')
        self.fecha_entrega_estimada = order_data.get('fecha_entrega_estimada')
        self.estado = order_data.get('estado')
        self.valor_total = Decimal(str(order_data.get('valor_total')))
        self.id_cliente = uuid.UUID(order_data.get('id_cliente'))
        self.id_vendedor = uuid.UUID(order_data.get('id_vendedor'))
        self.id_bodega_origen = uuid.UUID(order_data.get('id_bodega_origen'))
        self.creado_por = uuid.UUID(order_data.get('creado_por'))
        self.observaciones = order_data.get('observaciones')

        detalles = order_data.get('detalles', [])
        self.detalles = json.dumps(detalles)
        self.cantidad_items = sum(item.get('cantidad') for item in detalles)
        self.processed_at = datetime.utcnow()

    def to_dict(self):
        return {
            "id": str(self.id),
            "numero_orden": self.numero_orden,
            "fecha_creacion": self.fecha_creacion,
            "fecha_actualizacion": self.fecha_actualizacion,
            "fecha_entrega_estimada": self.fecha_entrega_estimada,
            "estado": self.estado,
            "valor_total": float(self.valor_total),
            "id_cliente": str(self.id_cliente),
            "id_vendedor": str(self.id_vendedor),
            "id_bodega_origen": str(self.id_bodega_origen),
            "creado_por": str(self.creado_por),
            "cantidad_items": self.cantidad_items,
            "observaciones": self.observaciones,
            "detalles": json.loads(self.detalles) if self.detalles else [],
        }

    def to_summary_dict(self):
        return {
            "id": str(self.id),
            "numero_orden": self.numero_orden,
            "fecha_creacion": self.fecha_creacion,
            "estado": self.estado,
            "valor_total": float(self.valor_total),
            "id_cliente": str(self.id_cliente),
            "cantidad_items": self.cantidad_items,
            "fecha_entrega_estimada": self.fecha_entrega_estimada,
        }
