from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from ..db.database import get_db
from fastapi import Depends
from ..db.order_projection_model import OrderProjection
from fastapi import HTTPException
from http import HTTPStatus
from .cache_service import CacheService
from datetime import datetime
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

    def list_orders(
        self,
        estado: Optional[str] = None,
        fecha_creacion_desde: Optional[datetime] = None,
        fecha_creacion_hasta: Optional[datetime] = None,
        skip: int = 0,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """List orders with optional filters and pagination.
        
        Args:
            estado: Filter by order status (optional)
            fecha_creacion_desde: Filter by creation date from (optional)
            fecha_creacion_hasta: Filter by creation date to (optional)
            skip: Number of records to skip (pagination)
            limit: Maximum number of records to return
            
        Returns:
            List of orders
        """
        try:
            query = self.db.query(OrderProjection)
            
            if estado:
                query = query.filter(OrderProjection.estado == estado)
            
            if fecha_creacion_desde:
                query = query.filter(OrderProjection.fecha_creacion >= fecha_creacion_desde)
            
            if fecha_creacion_hasta:
                query = query.filter(OrderProjection.fecha_creacion <= fecha_creacion_hasta)
            
            query = query.order_by(OrderProjection.fecha_creacion.desc())
            
            orders = query.offset(skip).limit(limit).all()
            
            orders_list = [order.to_dict() for order in orders]
            
            return orders_list
            
        except Exception as e:
            logger.error(f"Error listing orders: {e}")
            raise HTTPException(
                status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
                detail="Error interno al listar órdenes."
            )

    def count_orders(
        self,
        estado: Optional[str] = None,
        fecha_creacion_desde: Optional[datetime] = None,
        fecha_creacion_hasta: Optional[datetime] = None
    ) -> int:
        """Count total number of orders with optional filters.
        
        Args:
            estado: Filter by order status (optional)
            fecha_creacion_desde: Filter by creation date from (optional)
            fecha_creacion_hasta: Filter by creation date to (optional)
            
        Returns:
            Total number of orders
        """
        try:
            query = self.db.query(OrderProjection)
            
            if estado:
                query = query.filter(OrderProjection.estado == estado)
            
            if fecha_creacion_desde:
                query = query.filter(OrderProjection.fecha_creacion >= fecha_creacion_desde)
            
            if fecha_creacion_hasta:
                query = query.filter(OrderProjection.fecha_creacion <= fecha_creacion_hasta)
            
            count = query.count()
            
            return count
            
        except Exception as e:
            logger.error(f"Error counting orders: {e}")
            raise HTTPException(
                status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
                detail="Error interno al contar órdenes."
            )