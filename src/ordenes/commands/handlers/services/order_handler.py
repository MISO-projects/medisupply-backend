from typing import Dict, Any, List, Tuple 
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from ..db.order_model import Orden, DetalleOrden
from fastapi import Depends
from ..db.database import get_db
from datetime import datetime, timedelta, timezone
from ..services.pubsub_service import PubSubService
from ..services.pubsub_service import get_pubsub_service
import logging
import httpx  
import os     

logger = logging.getLogger(__name__)


class OrderHandler:
    def __init__(
        self,
        db: Session = Depends(get_db),
        pubsub_service: PubSubService = Depends(get_pubsub_service),
    ):
        self.db = db
        self.pubsub_service = pubsub_service
        self.inventario_service_url = os.getenv(
            "INVENTARIO_SERVICE_URL", "http://inventario-service:3000"
        )

    async def _disminuir_stock_inventario(self, orden: Orden) -> Tuple[bool, List[str]]:
        """
        Intenta disminuir el stock para todos los items de la orden.
        Retorna (exito_total, lista_de_errores)
        """
        logger.info(f"Iniciando disminución de stock para orden {orden.id}")
        errores = []
        
        async with httpx.AsyncClient(timeout=10.0) as client:
            for detalle in orden.detalles:
                payload = {
                    "producto_id": str(detalle.id_producto),
                    "cantidad_producto_solicitada": detalle.cantidad
                }
                try:
                    response = await client.put(
                        f"{self.inventario_service_url}/api/inventario/registro/pedido",
                        json=payload,
                        headers={"Content-Type": "application/json"}
                    )
                    
                    if response.status_code != 200:
                        error_msg = f"Producto {detalle.id_producto}: {response.json().get('detail', response.text)}"
                        logger.error(f"Error al disminuir stock: {error_msg}")
                        errores.append(error_msg)
                    else:
                        logger.info(f"Stock disminuido para producto {detalle.id_producto} (Cantidad: {detalle.cantidad})")
                
                except httpx.RequestError as e:
                    error_msg = f"Producto {detalle.id_producto}: Error de conexión con inventario ({e})"
                    logger.error(error_msg)
                    errores.append(error_msg)
        
        return len(errores) == 0, errores

    def _compensar_orden_fallida(self, orden: Orden, errores: List[str]):
        """
        Transacción de COMPENSACIÓN.
        Marca la orden como CANCELADA si la reducción de stock falla.
        """
        try:
            logger.warning(f"Iniciando compensación para orden {orden.id}...")
            orden.estado = "CANCELADO"
            orden.observaciones = (orden.observaciones or "") + \
                f"\n[ERROR_STOCK]: {'; '.join(errores)}"
            self.db.add(orden)
            self.db.commit()
            self.db.refresh(orden)
            logger.warning(f"Orden {orden.id} compensada y marcada como CANCELADA por error de stock.")
            
            # Evento "order_failed"
            # self.pubsub_service.publish_order_failed_event(orden.to_dict(), errores)
            
        except Exception as e:
            self.db.rollback()
            logger.critical(f"¡¡FALLO CRÍTICO!! No se pudo compensar la orden {orden.id}. Estado inconsistente. Error: {e}")

    async def handle_order(self, order_data: Dict[str, Any]): # <-- CAMBIADO A ASYNC
        try:
            existing_order = self.db.query(Orden).filter(
                Orden.id == order_data["id"]
            ).first()
            
            if existing_order:
                logger.info(f"Order with ID {order_data['id']} already exists. Skipping duplicate message.")
                return existing_order
            
            # Calculate fecha_entrega_estimada as 2 days from now
            fecha_entrega_estimada = datetime.now(timezone.utc) + timedelta(days=2)
            
            order = Orden(
                id=order_data["id"],
                numero_orden=order_data["numero_orden"],
                estado="PENDIENTE",
                fecha_entrega_estimada=fecha_entrega_estimada,
                observaciones=order_data["observaciones"],
                id_cliente=order_data["id_cliente"],
                id_vendedor=order_data["id_vendedor"],
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
            logger.info(f"Orden {order.id} creada. Procediendo a disminuir stock...")
            exito_stock, errores_stock = await self._disminuir_stock_inventario(order)
            
            if not exito_stock:
                self._compensar_orden_fallida(order, errores_stock)
                return order

            self.publish_order_created_event(order)
            return order
            
        except IntegrityError as e:
            pass 
        except Exception as e:
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
