from .pubsub_service import PubSubService
from typing import Dict, Any
from datetime import datetime
import uuid


class OrderService:
    def __init__(self, pubsub_service: PubSubService = None):
        self.pubsub_service = pubsub_service or PubSubService()

    def generar_numero_orden(self):
        date_part = datetime.now().strftime('%y%m%d')
        uuid_part = str(uuid.uuid4())[:8].upper()
        return f"ORD-{date_part}-{uuid_part}"

    def create_order(self, order_data: Dict[str, Any]) -> Dict[str, Any]:
        id = uuid.uuid4()
        order_data["id"] = str(id)
        order_data["numero_orden"] = self.generar_numero_orden()
        result = self.pubsub_service.publish_create_order_command(order_data)
        if not result:
            raise Exception("Failed to publish create order command")
        return {"id": id, "numero_orden": order_data["numero_orden"]}
