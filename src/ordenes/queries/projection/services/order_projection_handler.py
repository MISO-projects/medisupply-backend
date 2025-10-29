from typing import Dict, Any
from sqlalchemy.orm import Session
from db.order_projection_model import OrderProjection
from db.database import get_db
from fastapi import Depends
from http import HTTPStatus
from fastapi import HTTPException
import logging
from services.pubsub_service import PubSubService

logger = logging.getLogger(__name__)


class OrderProjectionHandler:
    def __init__(self, db: Session = Depends(get_db)):
        self.db = db
        self.pubsub_service = PubSubService()

    def handle_order_created_event(self, event_data: Dict[str, Any]):
        try:
            projection = OrderProjection(event_data)

            self.db.add(projection)
            self.db.commit()
            self.db.refresh(projection)

            logger.info(f"Order projection created for order: {projection.numero_orden}")
            
            self._publish_projection_created_event(projection)
            
            return projection.to_dict()

        except Exception as e:
            logger.error(f"Error creating projection: {str(e)}")
            raise HTTPException(
                status_code=HTTPStatus.BAD_REQUEST,
                detail='Error creating projection.',
            )

    def _publish_projection_created_event(self, projection: OrderProjection):
        """
        Publish an event when an order projection is created/updated.
        Other services (like the query API) can subscribe to this event to invalidate their caches.
        
        Args:
            projection: The order projection that was created/updated
        """
        try:
            projection_data = projection.to_dict()
            
            success = self.pubsub_service.publish_projection_created_event(projection_data)
            
            if success:
                logger.info(f"Published projection created event for order {projection.numero_orden}")
            else:
                logger.warning(f"Failed to publish projection created event for order {projection.numero_orden}")
            
        except Exception as e:
            # Don't fail the projection creation if event publishing fails
            logger.warning(f"Error publishing projection created event for order {projection.numero_orden}: {str(e)}")
