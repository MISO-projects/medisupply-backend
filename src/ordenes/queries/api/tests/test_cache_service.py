import pytest
from unittest.mock import Mock, MagicMock, patch
import json
from services.cache_service import CacheService


@pytest.fixture
def mock_redis_client():
    """Mock Redis client"""
    client = Mock()
    client.ping.return_value = True
    return client


@pytest.fixture
def cache_service_with_redis(mock_redis_client):
    """Cache service with mocked Redis"""
    with patch('services.cache_service.get_redis_client', return_value=mock_redis_client):
        service = CacheService(default_ttl=300)
        service.redis_client = mock_redis_client
        return service


@pytest.fixture
def cache_service_without_redis():
    """Cache service without Redis"""
    with patch('services.cache_service.get_redis_client', return_value=None):
        return CacheService()


class TestCacheServiceClientOrders:
    """Tests for client orders caching functionality"""

    def test_get_client_orders_cache_hit(self, cache_service_with_redis, mock_redis_client):
        """Test getting client orders from cache - cache hit"""
        client_id = "client-123"
        skip = 0
        limit = 20
        expected_data = [{"id": "order-1", "cliente_id": client_id}]
        
        mock_redis_client.get.return_value = json.dumps(expected_data)
        
        result = cache_service_with_redis.get_client_orders(client_id, skip, limit)
        
        assert result == expected_data
        mock_redis_client.get.assert_called_once_with(f"client_orders:{client_id}:skip:{skip}:limit:{limit}")

    def test_get_client_orders_cache_miss(self, cache_service_with_redis, mock_redis_client):
        """Test getting client orders from cache - cache miss"""
        client_id = "client-123"
        skip = 0
        limit = 20
        
        mock_redis_client.get.return_value = None
        
        result = cache_service_with_redis.get_client_orders(client_id, skip, limit)
        
        assert result is None
        mock_redis_client.get.assert_called_once()

    def test_get_client_orders_no_redis(self, cache_service_without_redis):
        """Test getting client orders when Redis is not available"""
        result = cache_service_without_redis.get_client_orders("client-123", 0, 20)
        
        assert result is None

    def test_get_client_orders_json_decode_error(self, cache_service_with_redis, mock_redis_client):
        """Test getting client orders with invalid JSON"""
        client_id = "client-123"
        mock_redis_client.get.return_value = "invalid json"
        
        result = cache_service_with_redis.get_client_orders(client_id, 0, 20)
        
        assert result is None
        # Should attempt to delete corrupted cache
        mock_redis_client.delete.assert_called_once()

    def test_set_client_orders_success(self, cache_service_with_redis, mock_redis_client):
        """Test successfully caching client orders"""
        client_id = "client-123"
        skip = 0
        limit = 20
        orders_data = [{"id": "order-1", "cliente_id": client_id}]
        
        mock_redis_client.setex.return_value = True
        
        result = cache_service_with_redis.set_client_orders(client_id, skip, limit, orders_data)
        
        assert result is True
        mock_redis_client.setex.assert_called_once()
        call_args = mock_redis_client.setex.call_args
        assert call_args[0][0] == f"client_orders:{client_id}:skip:{skip}:limit:{limit}"
        assert call_args[0][1] == 300  # default TTL
        assert json.loads(call_args[0][2]) == orders_data

    def test_set_client_orders_custom_ttl(self, cache_service_with_redis, mock_redis_client):
        """Test caching client orders with custom TTL"""
        client_id = "client-123"
        orders_data = [{"id": "order-1"}]
        custom_ttl = 600
        
        mock_redis_client.setex.return_value = True
        
        result = cache_service_with_redis.set_client_orders(
            client_id, 0, 20, orders_data, ttl=custom_ttl
        )
        
        assert result is True
        call_args = mock_redis_client.setex.call_args
        assert call_args[0][1] == custom_ttl

    def test_set_client_orders_no_redis(self, cache_service_without_redis):
        """Test caching client orders when Redis is not available"""
        result = cache_service_without_redis.set_client_orders(
            "client-123", 0, 20, [{"id": "order-1"}]
        )
        
        assert result is False

    def test_set_client_orders_failure(self, cache_service_with_redis, mock_redis_client):
        """Test caching client orders when setex fails"""
        mock_redis_client.setex.return_value = False
        
        result = cache_service_with_redis.set_client_orders(
            "client-123", 0, 20, [{"id": "order-1"}]
        )
        
        assert result is False

    def test_invalidate_client_orders_success(self, cache_service_with_redis, mock_redis_client):
        """Test invalidating all client orders cache"""
        client_id = "client-123"
        
        # Mock scan_iter to return some keys
        mock_keys = [
            b"client_orders:client-123:skip:0:limit:20",
            b"client_orders:client-123:skip:20:limit:20",
        ]
        mock_redis_client.scan_iter.return_value = iter(mock_keys)
        mock_redis_client.delete.return_value = 1
        
        result = cache_service_with_redis.invalidate_client_orders(client_id)
        
        assert result is True
        assert mock_redis_client.delete.call_count == 2
        mock_redis_client.scan_iter.assert_called_once_with(match=f"client_orders:{client_id}:*")

    def test_invalidate_client_orders_no_keys(self, cache_service_with_redis, mock_redis_client):
        """Test invalidating client orders when no keys exist"""
        client_id = "client-123"
        
        mock_redis_client.scan_iter.return_value = iter([])
        
        result = cache_service_with_redis.invalidate_client_orders(client_id)
        
        assert result is False

    def test_invalidate_client_orders_no_redis(self, cache_service_without_redis):
        """Test invalidating client orders when Redis is not available"""
        result = cache_service_without_redis.invalidate_client_orders("client-123")
        
        assert result is False

    def test_get_client_orders_key_generation(self, cache_service_with_redis):
        """Test cache key generation for client orders"""
        client_id = "client-123"
        skip = 40
        limit = 10
        
        key = cache_service_with_redis._get_client_orders_key(client_id, skip, limit)
        
        assert key == f"client_orders:{client_id}:skip:{skip}:limit:{limit}"

    def test_cache_key_uniqueness(self, cache_service_with_redis):
        """Test that different pagination parameters create unique keys"""
        client_id = "client-123"
        
        key1 = cache_service_with_redis._get_client_orders_key(client_id, 0, 20)
        key2 = cache_service_with_redis._get_client_orders_key(client_id, 20, 20)
        key3 = cache_service_with_redis._get_client_orders_key(client_id, 0, 10)
        
        assert key1 != key2
        assert key1 != key3
        assert key2 != key3


class TestCacheServiceHealthAndStats:
    """Tests for cache health and statistics"""

    def test_health_check_healthy(self, cache_service_with_redis, mock_redis_client):
        """Test health check when Redis is healthy"""
        mock_redis_client.ping.return_value = True
        
        result = cache_service_with_redis.health_check()
        
        assert result is True

    def test_health_check_unhealthy(self, cache_service_with_redis, mock_redis_client):
        """Test health check when Redis is unhealthy"""
        mock_redis_client.ping.side_effect = Exception("Connection failed")
        
        result = cache_service_with_redis.health_check()
        
        assert result is False

    def test_health_check_no_redis(self, cache_service_without_redis):
        """Test health check when Redis is not available"""
        result = cache_service_without_redis.health_check()
        
        assert result is False

    def test_get_cache_stats_success(self, cache_service_with_redis, mock_redis_client):
        """Test getting cache statistics"""
        mock_redis_client.info.return_value = {
            "used_memory_human": "1.5M",
            "connected_clients": 5,
            "total_commands_processed": 1000,
            "keyspace_hits": 800,
            "keyspace_misses": 200,
        }
        
        result = cache_service_with_redis.get_cache_stats()
        
        assert result["status"] == "connected"
        assert result["memory_used"] == "1.5M"
        assert result["connected_clients"] == 5
        assert result["keyspace_hits"] == 800

    def test_get_cache_stats_no_redis(self, cache_service_without_redis):
        """Test getting cache statistics when Redis is not available"""
        result = cache_service_without_redis.get_cache_stats()
        
        assert result["status"] == "disconnected"

