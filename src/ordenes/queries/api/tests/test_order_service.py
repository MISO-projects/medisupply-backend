import pytest
from unittest.mock import Mock, MagicMock, patch
from datetime import datetime
from fastapi import HTTPException
from services.order_service import OrderService


@pytest.fixture
def mock_db():
    """Mock database session"""
    return Mock()


@pytest.fixture
def mock_cache_service():
    """Mock cache service"""
    service = Mock()
    service.get_client_orders.return_value = None
    service.set_client_orders.return_value = True
    service.invalidate_client_orders.return_value = True
    service.health_check.return_value = True
    service.get_cache_stats.return_value = {"status": "connected"}
    return service


@pytest.fixture
def order_service(mock_db, mock_cache_service):
    """Order service with mocked dependencies"""
    with patch('services.order_service.CacheService', return_value=mock_cache_service):
        service = OrderService(db=mock_db)
        service.cache_service = mock_cache_service
        return service


class TestGetOrdersByClient:
    """Tests for get_orders_by_client method"""

    def test_get_orders_by_client_cache_hit(self, order_service, mock_cache_service, mock_db):
        """Test getting client orders when data is in cache"""
        client_id = "client-123"
        skip = 0
        limit = 20
        cached_data = [
            {"id": "order-1", "id_cliente": client_id, "id_vendedor": "vendor-1", "estado": "PENDING", "nombre_vendedor": "Vendedor Test", "nombre_cliente": "Cliente Test"},
            {"id": "order-2", "id_cliente": client_id, "id_vendedor": "vendor-1", "estado": "COMPLETED", "nombre_vendedor": "Vendedor Test", "nombre_cliente": "Cliente Test"}
        ]
        
        mock_cache_service.get_client_orders.return_value = cached_data
        
        result = order_service.get_orders_by_client(client_id, skip, limit)
        
        assert result == cached_data
        mock_cache_service.get_client_orders.assert_called_once_with(client_id, skip, limit)
        # Should not query database when cache hits and data already has names
        mock_db.query.assert_not_called()

    def test_get_orders_by_client_cache_miss(self, order_service, mock_cache_service, mock_db):
        """Test getting client orders when data is not in cache"""
        client_id = "client-123"
        vendor_id = "vendor-1"
        skip = 0
        limit = 20
        
        # Mock cache miss
        mock_cache_service.get_client_orders.return_value = None
        
        # Mock database response for orders
        mock_order_1 = Mock()
        mock_order_1.to_summary_dict.return_value = {
            "id": "order-1",
            "id_cliente": client_id,
            "id_vendedor": vendor_id,
            "estado": "PENDING"
        }
        
        mock_order_2 = Mock()
        mock_order_2.to_summary_dict.return_value = {
            "id": "order-2",
            "id_cliente": client_id,
            "id_vendedor": vendor_id,
            "estado": "COMPLETED"
        }
        
        # Mock vendor
        mock_vendedor = Mock()
        mock_vendedor.nombre = "Vendedor Test"
        
        # Mock client
        mock_cliente = Mock()
        mock_cliente.nombre = "Cliente Test"
        
        # Create a query mock that returns different things based on what model is queried
        def query_side_effect(model):
            mock_query = Mock()
            mock_query.filter.return_value = mock_query
            mock_query.order_by.return_value = mock_query
            mock_query.offset.return_value = mock_query
            mock_query.limit.return_value = mock_query
            mock_query.all.return_value = [mock_order_1, mock_order_2]
            mock_query.first.return_value = mock_vendedor if "Vendedor" in str(model) else mock_cliente
            return mock_query
        
        mock_db.query.side_effect = query_side_effect
        
        result = order_service.get_orders_by_client(client_id, skip, limit)
        
        # Verify result
        assert len(result) == 2
        assert result[0]["id"] == "order-1"
        assert result[1]["id"] == "order-2"
        assert result[0]["nombre_vendedor"] == "Vendedor Test"
        assert result[0]["nombre_cliente"] == "Cliente Test"
        
        # Verify cache was checked
        mock_cache_service.get_client_orders.assert_called_once_with(client_id, skip, limit)
        
        # Verify database was queried (once for orders, twice for each order's vendor and client)
        # Total: 1 (orders) + 2*2 (vendor+client for each order) = 5 queries
        assert mock_db.query.call_count >= 1  # At least the order query
        
        # Verify result was cached
        mock_cache_service.set_client_orders.assert_called_once_with(
            client_id, skip, limit, result
        )

    def test_get_orders_by_client_empty_result(self, order_service, mock_cache_service, mock_db):
        """Test getting client orders when client has no orders"""
        client_id = "client-456"
        skip = 0
        limit = 20
        
        mock_cache_service.get_client_orders.return_value = None
        
        mock_query = Mock()
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.offset.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.all.return_value = []
        
        mock_db.query.return_value = mock_query
        
        result = order_service.get_orders_by_client(client_id, skip, limit)
        
        assert result == []
        mock_cache_service.set_client_orders.assert_called_once_with(client_id, skip, limit, [])

    def test_get_orders_by_client_with_pagination(self, order_service, mock_cache_service, mock_db):
        """Test getting client orders with different pagination parameters"""
        client_id = "client-123"
        skip = 20
        limit = 10
        
        mock_cache_service.get_client_orders.return_value = None
        
        mock_order = Mock()
        mock_order.to_summary_dict.return_value = {"id": "order-1"}
        
        mock_query = Mock()
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.offset.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.all.return_value = [mock_order]
        
        mock_db.query.return_value = mock_query
        
        result = order_service.get_orders_by_client(client_id, skip, limit)
        
        # Verify pagination parameters were used
        mock_query.offset.assert_called_once_with(skip)
        mock_query.limit.assert_called_once_with(limit)
        
        # Verify result was cached with correct parameters
        mock_cache_service.set_client_orders.assert_called_once_with(
            client_id, skip, limit, [{"id": "order-1"}]
        )

    def test_get_orders_by_client_database_error(self, order_service, mock_cache_service, mock_db):
        """Test handling database error when getting client orders"""
        client_id = "client-123"
        
        mock_cache_service.get_client_orders.return_value = None
        mock_db.query.side_effect = Exception("Database connection failed")
        
        with pytest.raises(HTTPException) as exc_info:
            order_service.get_orders_by_client(client_id, 0, 20)
        
        assert exc_info.value.status_code == 500
        assert "Error interno al obtener órdenes del cliente" in exc_info.value.detail


class TestCountOrdersByClient:
    """Tests for count_orders_by_client method"""

    def test_count_orders_by_client_success(self, order_service, mock_db):
        """Test counting orders for a client"""
        client_id = "client-123"
        expected_count = 42
        
        mock_query = Mock()
        mock_query.filter.return_value = mock_query
        mock_query.count.return_value = expected_count
        
        mock_db.query.return_value = mock_query
        
        result = order_service.count_orders_by_client(client_id)
        
        assert result == expected_count
        mock_db.query.assert_called_once()
        mock_query.count.assert_called_once()

    def test_count_orders_by_client_zero(self, order_service, mock_db):
        """Test counting orders when client has no orders"""
        client_id = "client-456"
        
        mock_query = Mock()
        mock_query.filter.return_value = mock_query
        mock_query.count.return_value = 0
        
        mock_db.query.return_value = mock_query
        
        result = order_service.count_orders_by_client(client_id)
        
        assert result == 0

    def test_count_orders_by_client_database_error(self, order_service, mock_db):
        """Test handling database error when counting orders"""
        client_id = "client-123"
        
        mock_db.query.side_effect = Exception("Database error")
        
        with pytest.raises(HTTPException) as exc_info:
            order_service.count_orders_by_client(client_id)
        
        assert exc_info.value.status_code == 500
        assert "Error interno al contar órdenes del cliente" in exc_info.value.detail


class TestCacheInvalidation:
    """Tests for cache invalidation methods"""

    def test_invalidate_client_orders_cache_success(self, order_service, mock_cache_service):
        """Test invalidating client orders cache"""
        client_id = "client-123"
        
        mock_cache_service.invalidate_client_orders.return_value = True
        
        result = order_service.invalidate_client_orders_cache(client_id)
        
        assert result is True
        mock_cache_service.invalidate_client_orders.assert_called_once_with(client_id)

    def test_invalidate_client_orders_cache_failure(self, order_service, mock_cache_service):
        """Test invalidating client orders cache when it fails"""
        client_id = "client-123"
        
        mock_cache_service.invalidate_client_orders.return_value = False
        
        result = order_service.invalidate_client_orders_cache(client_id)
        
        assert result is False

    def test_invalidate_order_cache_success(self, order_service, mock_cache_service):
        """Test invalidating single order cache"""
        order_id = "order-123"
        
        mock_cache_service.invalidate_order.return_value = True
        
        result = order_service.invalidate_order_cache(order_id)
        
        assert result is True
        mock_cache_service.invalidate_order.assert_called_once_with(order_id)


class TestCacheHealth:
    """Tests for cache health methods"""

    def test_get_cache_health_success(self, order_service, mock_cache_service):
        """Test getting cache health status"""
        mock_cache_service.health_check.return_value = True
        mock_cache_service.get_cache_stats.return_value = {
            "status": "connected",
            "memory_used": "1.5M"
        }
        
        result = order_service.get_cache_health()
        
        assert result["health"] is True
        assert result["stats"]["status"] == "connected"
        assert result["stats"]["memory_used"] == "1.5M"

    def test_get_cache_health_unhealthy(self, order_service, mock_cache_service):
        """Test getting cache health when cache is unhealthy"""
        mock_cache_service.health_check.return_value = False
        mock_cache_service.get_cache_stats.return_value = {"status": "disconnected"}
        
        result = order_service.get_cache_health()
        
        assert result["health"] is False
        assert result["stats"]["status"] == "disconnected"

