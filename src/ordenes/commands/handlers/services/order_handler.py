from typing import Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from ..db.order_model import Orden, DetalleOrden
from fastapi import Depends
from ..db.database import get_db
from datetime import datetime
from ..services.pubsub_service import PubSubService
from ..services.pubsub_service import get_pubsub_service
import logging

logger = logging.getLogger(__name__)


class OrderHandler:
    def __init__(
        self,
        db: Session = Depends(get_db),
        pubsub_service: PubSubService = Depends(get_pubsub_service),
    ):
        self.db = db
        self.pubsub_service = pubsub_service

    def handle_order(self, order_data: Dict[str, Any]):
        try:
            existing_order = self.db.query(Orden).filter(
                Orden.id == order_data["id"]
            ).first()
            
            if existing_order:
                logger.info(f"Order with ID {order_data['id']} already exists. Skipping duplicate message.")
                return existing_order
            
            order = Orden(
                id=order_data["id"],
                numero_orden=order_data["numero_orden"],
                estado="PENDIENTE",
                fecha_entrega_estimada=datetime.fromisoformat(
                    order_data["fecha_entrega_estimada"]
                ),
                observaciones=order_data["observaciones"],
                id_cliente=order_data["id_cliente"],
                id_vendedor=order_data["id_vendedor"],
                id_bodega_origen=order_data["id_bodega_origen"],
                creado_por=order_data["creado_por"],
            )
            detalle_orden = []
            valor_total = 0
            for detalle in order_data["detalles"]:
                valor_total += detalle["precio_unitario"] * detalle["cantidad"]
                detalle_orden.append(
                    DetalleOrden(
                        id_orden=order.id,
                        id_producto=detalle["id_producto"],
                        cantidad=detalle["cantidad"],
                        precio_unitario=detalle["precio_unitario"],
                        observaciones=detalle["observaciones"],
                    )
                )
            order.detalles = detalle_orden
            order.valor_total = valor_total
            self.db.add(order)
            self.db.commit()
            self.db.refresh(order)
            self.publish_order_created_event(order)
            return order
            
        except IntegrityError as e:
            self.db.rollback()
            logger.warning(f"Duplicate message received for order ID {order_data.get('id')} or numero_orden {order_data.get('numero_orden')}: {str(e)}")
            
            existing_order = self.db.query(Orden).filter(
                Orden.id == order_data["id"]
            ).first()
            
            if not existing_order:
                existing_order = self.db.query(Orden).filter(
                    Orden.numero_orden == order_data["numero_orden"]
                ).first()
            
            if existing_order:
                logger.info(f"Returning existing order: {existing_order.id}")
                return existing_order
            else:
                logger.error(f"IntegrityError occurred but couldn't find existing order for ID {order_data.get('id')}")
                raise

    def publish_order_created_event(self, orden: Orden):
        order_data = orden.to_dict()
        order_data["detalles"] = [detalle.to_dict() for detalle in orden.detalles]
        self.pubsub_service.publish_order_created_event(order_data)
