from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from db.database import get_db
from fastapi import Depends
from db.order_projection_model import OrderProjection
from db.vendedor_model import Vendedor
from db.cliente_model import ClienteInstitucional
from fastapi import HTTPException
from http import HTTPStatus
from services.cache_service import CacheService
from datetime import datetime
import logging
import httpx  
import os     
from sqlalchemy import func, desc
logger = logging.getLogger(__name__)
try:
    from db.order_model import Orden, DetalleOrden
except ImportError:
    logger.error("Error importando Orden y DetalleOrden. Asegúrate de copiar 'order_model.py' a la carpeta 'db' de 'queries'.")
    class Orden: pass
    class DetalleOrden: pass
logger = logging.getLogger(__name__)


class OrderService:
    def __init__(self, db: Session = Depends(get_db)):
        self.db = db
        self.cache_service = CacheService()
        self.productos_service_url = os.getenv(
            "PRODUCTOS_SERVICE_URL", "http://productos-service:3000" 
        )

    async def _get_products_batch_data(self, product_ids: List[str]) -> List[Dict[str, Any]]:
        """
        Llama al servicio de Productos (usando /by-ids) para obtener los
        nombres y detalles de una lista de IDs.
        """
        if not product_ids:
            return []
        
        request_body = {"ids": product_ids}
        endpoint_url = f"{self.productos_service_url}/api/productos/by-ids" 
        
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.post(endpoint_url, json=request_body)
            
            if response.status_code == HTTPStatus.OK:
                return response.json()
            else:
                logger.error(f"Error del servicio de productos ({endpoint_url}): {response.status_code} - {response.text}")
                return []
        
        except httpx.RequestError as e:
            logger.error(f"Error de conexión al servicio de productos ({endpoint_url}): {e}")
            return []

    def _enrich_order_with_names(self, order_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Enriquece los datos de una orden con los nombres de vendedor y cliente.
        
        Args:
            order_data: Diccionario con los datos de la orden
            
        Returns:
            Diccionario enriquecido con nombre_vendedor y nombre_cliente
        """
        try:
            # Obtener nombre del vendedor
            if order_data.get('id_vendedor'):
                vendedor = self.db.query(Vendedor).filter(
                    Vendedor.id == order_data['id_vendedor']
                ).first()
                if vendedor:
                    order_data['nombre_vendedor'] = vendedor.nombre
                else:
                    order_data['nombre_vendedor'] = None
            
            # Obtener nombre del cliente
            if order_data.get('id_cliente'):
                cliente = self.db.query(ClienteInstitucional).filter(
                    ClienteInstitucional.id == order_data['id_cliente']
                ).first()
                if cliente:
                    order_data['nombre_cliente'] = cliente.nombre
                else:
                    order_data['nombre_cliente'] = None
            
            return order_data
        except Exception as e:
            logger.warning(f"Error enriching order data: {e}")
            # Si falla, devolver los datos sin enriquecer
            order_data['nombre_vendedor'] = None
            order_data['nombre_cliente'] = None
            return order_data

    def get_order(self, order_id: str) -> Dict[str, Any]:
        cached_order = self.cache_service.get_order(order_id)
        if cached_order:
            # Enriquecer datos cacheados si no tienen los nombres
            if 'nombre_vendedor' not in cached_order or 'nombre_cliente' not in cached_order:
                return self._enrich_order_with_names(cached_order)
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
        
        # Enriquecer con nombres de vendedor y cliente
        order_data = self._enrich_order_with_names(order_data)
        
        self.cache_service.set_order(order_id, order_data)
        
        return order_data

    def invalidate_order_cache(self, order_id: str) -> bool:
        """Invalidate cache for a specific order"""
        return self.cache_service.invalidate_order(order_id)

    def invalidate_client_orders_cache(self, client_id: str) -> bool:
        """Invalidate all cached orders for a specific client"""
        return self.cache_service.invalidate_client_orders(client_id)

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
        return [str(order.id) for order in orders]

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
            List of orders enriched with vendor and client names
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
            
            # Enriquecer cada orden con nombres de vendedor y cliente
            enriched_orders = [self._enrich_order_with_names(order) for order in orders_list]
            
            return enriched_orders
            
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

    def get_orders_by_client(
        self,
        id_cliente: str,
        skip: int = 0,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Get all orders for a specific client with pagination.
        
        Args:
            id_cliente: The ID of the client
            skip: Number of records to skip (pagination)
            limit: Maximum number of records to return
            
        Returns:
            List of orders for the specified client enriched with vendor and client names
        """
        try:
            # Try to get from cache first
            cached_orders = self.cache_service.get_client_orders(id_cliente, skip, limit)
            if cached_orders:
                # Enriquecer datos cacheados si no tienen los nombres
                if cached_orders and ('nombre_vendedor' not in cached_orders[0] if cached_orders else False):
                    return [self._enrich_order_with_names(order) for order in cached_orders]
                return cached_orders
            
            logger.info(f"Getting orders for client {id_cliente} from database")
            orders = (
                self.db.query(OrderProjection)
                .filter(OrderProjection.id_cliente == id_cliente)
                .order_by(OrderProjection.fecha_creacion.desc())
                .offset(skip)
                .limit(limit)
                .all()
            )
            
            orders_list = [order.to_summary_dict() for order in orders]
            
            # Enriquecer cada orden con nombres de vendedor y cliente
            enriched_orders = [self._enrich_order_with_names(order) for order in orders_list]
            
            # Cache the result
            self.cache_service.set_client_orders(id_cliente, skip, limit, enriched_orders)
            
            return enriched_orders
            
        except Exception as e:
            logger.error(f"Error getting orders for client {id_cliente}: {e}")
            raise HTTPException(
                status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
                detail="Error interno al obtener órdenes del cliente."
            )

    def count_orders_by_client(self, id_cliente: str) -> int:
        """Count total number of orders for a specific client.
        
        Args:
            id_cliente: The ID of the client
            
        Returns:
            Total number of orders for the client
        """
        try:
            count = (
                self.db.query(OrderProjection)
                .filter(OrderProjection.id_cliente == id_cliente)
                .count()
            )
            
            return count
            
        except Exception as e:
            logger.error(f"Error counting orders for client {id_cliente}: {e}")
            raise HTTPException(
                status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
                detail="Error interno al contar órdenes del cliente."
            )
        
    async def get_top_products_by_client(
        self,
        id_cliente: str,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Calcula los productos más solicitados por un cliente usando agregación SQL
        directamente en las tablas 'ordenes' y 'detalles_ordenes'.
        """
        try:
            top_products_query = (
                self.db.query(
                    DetalleOrden.id_producto,
                    func.sum(DetalleOrden.cantidad).label("cantidad_total")
                )
                .join(Orden, Orden.id == DetalleOrden.id_orden)
                .filter(Orden.id_cliente == id_cliente)
                .group_by(DetalleOrden.id_producto)
                .order_by(desc("cantidad_total")) 
                .limit(limit)
            )
            
            top_products_db = top_products_query.all()

            if not top_products_db:
                return []

            product_ids = [str(p.id_producto) for p in top_products_db]
            
            products_data_list = await self._get_products_batch_data(product_ids)
            products_map = {p.get("id"): p for p in products_data_list}

            result = []
            for product_stat in top_products_db:
                pid = str(product_stat.id_producto)
                product_info = products_map.get(pid, {})
                
                result.append({
                    "id_producto": pid,
                    "nombre": product_info.get("nombre", "Nombre no encontrado"),
                    "cantidad_total": int(product_stat.cantidad_total)
                })

            return result

        except Exception as e:
            logger.error(f"Error calculando top products para cliente {id_cliente}: {e}")
            raise HTTPException(
                status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
                detail="Error interno al calcular productos más solicitados."
            )


def get_order_service(db: Session = Depends(get_db)) -> OrderService:
    """Dependency function to get OrderService instance"""
    return OrderService(db=db)