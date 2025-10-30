import pytest
import json
import base64
from unittest.mock import Mock
from fastapi.testclient import TestClient
from main import app
from services.order_service import get_order_service


@pytest.fixture
def mock_order_service():
    """Mock order service for cache invalidation tests"""
    service = Mock()
    service.invalidate_order_cache = Mock(return_value=True)
    service.invalidate_client_orders_cache = Mock(return_value=True)
    return service


@pytest.fixture
def client(mock_order_service):
    """Test client with mocked dependencies"""
    app.dependency_overrides[get_order_service] = lambda: mock_order_service
    test_client = TestClient(app)
    yield test_client
    app.dependency_overrides.clear()


def create_pubsub_message(event_data: dict) -> dict:
    """Helper to create Pub/Sub message format"""
    message_json = json.dumps(event_data)
    message_bytes = message_json.encode("utf-8")
    message_base64 = base64.b64encode(message_bytes).decode("utf-8")
    
    return {
        "message": {
            "data": message_base64,
            "messageId": "test-message-id",
            "publishTime": "2024-01-01T10:00:00.000Z"
        },
        "subscription": "projects/test-project/subscriptions/order-projection-created-sub"
    }


class TestCacheInvalidationEndpoint:
    """Tests for POST /orders/cache-invalidation endpoint"""

    def test_cache_invalidation_success(self, client, mock_order_service):
        """Test successful cache invalidation"""
        event_data = {
            "event_type": "order_projection_created",
            "timestamp": "2024-01-01T10:00:00",
            "order_id": "order-123",
            "client_id": "client-456",
            "numero_orden": "ORD-2024-001"
        }
        
        pubsub_message = create_pubsub_message(event_data)
        
        response = client.post(
            "/orders/cache-invalidation",
            json=pubsub_message
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert "order:order-123" in data["invalidated"]
        assert "client_orders:client-456" in data["invalidated"]
        assert data["event_type"] == "order_projection_created"
        assert data["order_id"] == "order-123"
        assert data["client_id"] == "client-456"
        
        # Verify cache invalidation methods were called
        mock_order_service.invalidate_order_cache.assert_called_once_with("order-123")
        mock_order_service.invalidate_client_orders_cache.assert_called_once_with("client-456")

    def test_cache_invalidation_only_order_id(self, client, mock_order_service):
        """Test cache invalidation with only order_id"""
        event_data = {
            "event_type": "order_projection_created",
            "order_id": "order-789",
            "client_id": None
        }
        
        pubsub_message = create_pubsub_message(event_data)
        
        response = client.post(
            "/orders/cache-invalidation",
            json=pubsub_message
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert "order:order-789" in data["invalidated"]
        assert len(data["invalidated"]) == 1
        
        mock_order_service.invalidate_order_cache.assert_called_once_with("order-789")
        mock_order_service.invalidate_client_orders_cache.assert_not_called()

    def test_cache_invalidation_only_client_id(self, client, mock_order_service):
        """Test cache invalidation with only client_id"""
        event_data = {
            "event_type": "order_projection_created",
            "order_id": None,
            "client_id": "client-999"
        }
        
        pubsub_message = create_pubsub_message(event_data)
        
        response = client.post(
            "/orders/cache-invalidation",
            json=pubsub_message
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert "client_orders:client-999" in data["invalidated"]
        assert len(data["invalidated"]) == 1
        
        mock_order_service.invalidate_order_cache.assert_not_called()
        mock_order_service.invalidate_client_orders_cache.assert_called_once_with("client-999")

    def test_cache_invalidation_no_ids(self, client, mock_order_service):
        """Test cache invalidation with no order_id or client_id"""
        event_data = {
            "event_type": "order_projection_created",
            "timestamp": "2024-01-01T10:00:00"
        }
        
        pubsub_message = create_pubsub_message(event_data)
        
        response = client.post(
            "/orders/cache-invalidation",
            json=pubsub_message
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert data["invalidated"] == []
        
        mock_order_service.invalidate_order_cache.assert_not_called()
        mock_order_service.invalidate_client_orders_cache.assert_not_called()

    def test_cache_invalidation_service_fails(self, client, mock_order_service):
        """Test when cache invalidation service methods return False"""
        mock_order_service.invalidate_order_cache.return_value = False
        mock_order_service.invalidate_client_orders_cache.return_value = False
        
        event_data = {
            "event_type": "order_projection_created",
            "order_id": "order-123",
            "client_id": "client-456"
        }
        
        pubsub_message = create_pubsub_message(event_data)
        
        response = client.post(
            "/orders/cache-invalidation",
            json=pubsub_message
        )
        
        # Should still return 200 (acknowledge the message)
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        # No entries in invalidated list since methods returned False
        assert data["invalidated"] == []

    def test_cache_invalidation_no_message_field(self, client, mock_order_service):
        """Test handling of Pub/Sub message without 'message' field"""
        response = client.post(
            "/orders/cache-invalidation",
            json={"subscription": "test-sub"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ignored"
        assert data["reason"] == "no message field"
        
        mock_order_service.invalidate_order_cache.assert_not_called()

    def test_cache_invalidation_no_data_field(self, client, mock_order_service):
        """Test handling of Pub/Sub message without 'data' field"""
        response = client.post(
            "/orders/cache-invalidation",
            json={"message": {"messageId": "123"}}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ignored"
        assert data["reason"] == "no data"
        
        mock_order_service.invalidate_order_cache.assert_not_called()

    def test_cache_invalidation_empty_data_field(self, client, mock_order_service):
        """Test handling of Pub/Sub message with empty 'data' field"""
        response = client.post(
            "/orders/cache-invalidation",
            json={"message": {"data": "", "messageId": "123"}}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ignored"
        assert data["reason"] == "no data"

    def test_cache_invalidation_invalid_base64(self, client, mock_order_service):
        """Test handling of invalid base64 data"""
        response = client.post(
            "/orders/cache-invalidation",
            json={"message": {"data": "not-valid-base64!!!", "messageId": "123"}}
        )
        
        # Should return 200 to acknowledge the message (avoid retries)
        assert response.status_code == 200

    def test_cache_invalidation_invalid_json(self, client, mock_order_service):
        """Test handling of invalid JSON in message data"""
        invalid_json = "not valid json"
        message_base64 = base64.b64encode(invalid_json.encode("utf-8")).decode("utf-8")
        
        response = client.post(
            "/orders/cache-invalidation",
            json={"message": {"data": message_base64, "messageId": "123"}}
        )
        
        # Should return 200 to acknowledge the message
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "error"
        assert data["reason"] == "invalid json"

    def test_cache_invalidation_service_exception(self, client, mock_order_service):
        """Test handling when service raises an exception"""
        mock_order_service.invalidate_order_cache.side_effect = Exception("Cache error")
        
        event_data = {
            "event_type": "order_projection_created",
            "order_id": "order-123",
            "client_id": "client-456"
        }
        
        pubsub_message = create_pubsub_message(event_data)
        
        response = client.post(
            "/orders/cache-invalidation",
            json=pubsub_message
        )
        
        # Should return 200 to acknowledge the message (cache invalidation is not critical)
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "error"
        assert "Cache error" in data["reason"]

    def test_cache_invalidation_multiple_events(self, client, mock_order_service):
        """Test multiple cache invalidation requests"""
        events = [
            {
                "event_type": "order_projection_created",
                "order_id": f"order-{i}",
                "client_id": f"client-{i}",
                "numero_orden": f"ORD-{i}"
            }
            for i in range(3)
        ]
        
        for event_data in events:
            pubsub_message = create_pubsub_message(event_data)
            
            response = client.post(
                "/orders/cache-invalidation",
                json=pubsub_message
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "success"
        
        # Verify all events were processed
        assert mock_order_service.invalidate_order_cache.call_count == 3
        assert mock_order_service.invalidate_client_orders_cache.call_count == 3

    def test_cache_invalidation_preserves_event_metadata(self, client, mock_order_service):
        """Test that response includes all event metadata"""
        event_data = {
            "event_type": "order_projection_created",
            "timestamp": "2024-01-01T10:00:00.123Z",
            "order_id": "order-xyz",
            "client_id": "client-abc",
            "numero_orden": "ORD-XYZ-001"
        }
        
        pubsub_message = create_pubsub_message(event_data)
        
        response = client.post(
            "/orders/cache-invalidation",
            json=pubsub_message
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["event_type"] == "order_projection_created"
        assert data["order_id"] == "order-xyz"
        assert data["client_id"] == "client-abc"

    def test_cache_invalidation_handles_unicode(self, client, mock_order_service):
        """Test handling of unicode characters in event data"""
        event_data = {
            "event_type": "order_projection_created",
            "order_id": "order-123",
            "client_id": "client-456",
            "numero_orden": "ORD-2024-测试"  # Unicode characters
        }
        
        pubsub_message = create_pubsub_message(event_data)
        
        response = client.post(
            "/orders/cache-invalidation",
            json=pubsub_message
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"

    def test_cache_invalidation_real_pubsub_format(self, client, mock_order_service):
        """Test with exact Pub/Sub push subscription format"""
        # This is the exact format sent by Google Cloud Pub/Sub
        pubsub_payload = {
            "message": {
                "attributes": {
                    "key": "value"
                },
                "data": base64.b64encode(json.dumps({
                    "event_type": "order_projection_created",
                    "order_id": "order-real",
                    "client_id": "client-real"
                }).encode("utf-8")).decode("utf-8"),
                "messageId": "1234567890",
                "message_id": "1234567890",
                "publishTime": "2024-01-01T10:00:00.000Z",
                "publish_time": "2024-01-01T10:00:00.000Z"
            },
            "subscription": "projects/medisupply-474421/subscriptions/order-projection-created-sub"
        }
        
        response = client.post(
            "/orders/cache-invalidation",
            json=pubsub_payload
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        mock_order_service.invalidate_order_cache.assert_called_once_with("order-real")
        mock_order_service.invalidate_client_orders_cache.assert_called_once_with("client-real")

