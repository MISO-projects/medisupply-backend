from typing import Dict, Any
from sqlalchemy.orm import Session
from ..db.database import get_db
from fastapi import Depends
from ..db.order_projection_model import OrderProjection
from fastapi import HTTPException
from http import HTTPStatus
from .cache_service import CacheService
import logging

logger = logging.getLogger(__name__)


class OrderService:
    def __init__(self, db: Session = Depends(get_db)):
        self.db = db
        self.cache_service = CacheService()

    def get_order(self, order_id: str) -> Dict[str, Any]:
        cached_order = self.cache_service.get_order(order_id)
        if cached_order:
            return cached_order

        order = (
            self.db.query(OrderProjection)
            .filter(OrderProjection.id == order_id)
            .first()
        )
        
        if not order:
            raise HTTPException(
                status_code=HTTPStatus.NOT_FOUND,
                detail='Order not found.',
            )

        order_data = order.to_dict()
        
        self.cache_service.set_order(order_id, order_data)
        
        return order_data

    def invalidate_order_cache(self, order_id: str) -> bool:
        """Invalidate cache for a specific order"""
        return self.cache_service.invalidate_order(order_id)

    def get_cache_health(self) -> Dict[str, Any]:
        """Get cache health and statistics"""
        return {
            "health": self.cache_service.health_check(),
            "stats": self.cache_service.get_cache_stats()
        }

    def get_all_order_ids(self) -> list[str]:
        """Get a list of all order IDs from the database
        
        Returns:
            list[str]: List of order IDs
        """
        orders = self.db.query(OrderProjection.id).all()
        return [order.id for order in orders]