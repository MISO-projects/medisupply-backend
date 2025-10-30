import pytest
from unittest.mock import Mock, MagicMock, patch
from services.pubsub_service import PubSubService
from google.cloud import pubsub_v1


@pytest.fixture
def mock_publisher():
    """Mock Pub/Sub publisher client"""
    publisher = Mock(spec=pubsub_v1.PublisherClient)
    publisher.topic_path.return_value = "projects/test-project/topics/order-projection-created"
    return publisher


@pytest.fixture
def mock_future():
    """Mock future result for publish operation"""
    future = Mock()
    future.result.return_value = "message-id-123"
    return future


class TestPubSubServiceInitialization:
    """Tests for PubSubService initialization"""

    @patch.dict("os.environ", {"PUBSUB_EMULATOR_HOST": "localhost:8085"})
    @patch("services.pubsub_service.pubsub_v1.PublisherClient")
    def test_initialize_with_emulator(self, mock_publisher_class):
        """Test initialization with Pub/Sub emulator"""
        service = PubSubService(project_id="test-project")
        
        mock_publisher_class.assert_called_once()
        assert service.project_id == "test-project"
        assert service.topic_name == "order-projection-created"
        assert service._publisher is not None

    @patch.dict("os.environ", {"PUBSUB_EMULATOR_HOST": ""}, clear=True)
    @patch("os.path.exists", return_value=True)
    @patch("services.pubsub_service.Credentials.from_service_account_file")
    @patch("services.pubsub_service.pubsub_v1.PublisherClient")
    def test_initialize_with_service_account(
        self, mock_publisher_class, mock_credentials, mock_exists
    ):
        """Test initialization with service account file"""
        service = PubSubService(project_id="test-project")
        
        mock_credentials.assert_called_once_with("credentials.json")
        mock_publisher_class.assert_called_once()
        assert service._publisher is not None

    @patch.dict("os.environ", {"GOOGLE_CLOUD_PROJECT_ID": "env-project-id"})
    @patch.dict("os.environ", {"PUBSUB_EMULATOR_HOST": "localhost:8085"})
    @patch("services.pubsub_service.pubsub_v1.PublisherClient")
    def test_initialize_uses_env_variables(self, mock_publisher_class):
        """Test that initialization uses environment variables when not explicitly provided"""
        service = PubSubService()
        
        assert service.project_id == "env-project-id"
        assert service.topic_name == "order-projection-created"

    @patch.dict("os.environ", {"PUBSUB_EMULATOR_HOST": "localhost:8085"})
    @patch("services.pubsub_service.pubsub_v1.PublisherClient")
    def test_custom_topic_name(self, mock_publisher_class):
        """Test initialization with custom topic name"""
        service = PubSubService(
            project_id="test-project",
            topic_name="custom-topic"
        )
        
        assert service.topic_name == "custom-topic"


class TestPublishProjectionCreatedEvent:
    """Tests for publish_projection_created_event method"""

    @patch.dict("os.environ", {"PUBSUB_EMULATOR_HOST": "localhost:8085"})
    @patch("services.pubsub_service.pubsub_v1.PublisherClient")
    def test_publish_event_success(self, mock_publisher_class, mock_future):
        """Test successfully publishing a projection created event"""
        mock_publisher_instance = Mock()
        mock_publisher_instance.topic_path.return_value = "projects/test-project/topics/order-projection-created"
        mock_publisher_instance.publish.return_value = mock_future
        mock_publisher_class.return_value = mock_publisher_instance
        
        service = PubSubService(project_id="test-project")
        
        projection_data = {
            "id": "order-uuid-123",
            "id_cliente": "client-456",
            "numero_orden": "ORD-2024-001",
            "estado": "PENDING"
        }
        
        result = service.publish_projection_created_event(projection_data)
        
        assert result is True
        mock_publisher_instance.publish.assert_called_once()
        
        # Verify the published message contains expected keys
        call_args = mock_publisher_instance.publish.call_args
        assert call_args[0][0] == "projects/test-project/topics/order-projection-created"
        message_bytes = call_args[0][1]
        
        import json
        message_data = json.loads(message_bytes.decode("utf-8"))
        assert message_data["event_type"] == "order_projection_created"
        assert message_data["order_id"] == "order-uuid-123"
        assert message_data["client_id"] == "client-456"
        assert message_data["numero_orden"] == "ORD-2024-001"
        assert "timestamp" in message_data

    @patch.dict("os.environ", {"PUBSUB_EMULATOR_HOST": "localhost:8085"})
    @patch("services.pubsub_service.pubsub_v1.PublisherClient")
    def test_publish_event_extracts_correct_fields(self, mock_publisher_class, mock_future):
        """Test that event payload extracts only necessary fields"""
        mock_publisher_instance = Mock()
        mock_publisher_instance.topic_path.return_value = "projects/test-project/topics/order-projection-created"
        mock_publisher_instance.publish.return_value = mock_future
        mock_publisher_class.return_value = mock_publisher_instance
        
        service = PubSubService(project_id="test-project")
        
        # Projection data with extra fields
        projection_data = {
            "id": "order-123",
            "id_cliente": "client-456",
            "numero_orden": "ORD-001",
            "estado": "PENDING",
            "detalles": [{"producto": "Product A"}],  # Extra field
            "total": 100.50  # Extra field
        }
        
        result = service.publish_projection_created_event(projection_data)
        
        assert result is True
        
        # Verify only essential fields are published
        call_args = mock_publisher_instance.publish.call_args
        message_bytes = call_args[0][1]
        
        import json
        message_data = json.loads(message_bytes.decode("utf-8"))
        assert "order_id" in message_data
        assert "client_id" in message_data
        assert "numero_orden" in message_data
        assert "event_type" in message_data
        assert "timestamp" in message_data
        # Extra fields should not be in the event
        assert "detalles" not in message_data
        assert "total" not in message_data

    @patch.dict("os.environ", {"PUBSUB_EMULATOR_HOST": "localhost:8085"})
    @patch("services.pubsub_service.pubsub_v1.PublisherClient")
    def test_publish_event_publisher_not_initialized(self, mock_publisher_class):
        """Test publishing when publisher is not properly initialized"""
        service = PubSubService(project_id="test-project")
        service._publisher = None
        
        result = service.publish_projection_created_event({
            "id": "order-123",
            "id_cliente": "client-456",
            "numero_orden": "ORD-001"
        })
        
        assert result is False

    @patch.dict("os.environ", {"PUBSUB_EMULATOR_HOST": "localhost:8085"})
    @patch("services.pubsub_service.pubsub_v1.PublisherClient")
    def test_publish_event_no_project_id(self, mock_publisher_class):
        """Test publishing when project_id is not set"""
        mock_publisher_instance = Mock()
        mock_publisher_class.return_value = mock_publisher_instance
        
        service = PubSubService()
        service.project_id = None
        
        result = service.publish_projection_created_event({
            "id": "order-123",
            "id_cliente": "client-456",
            "numero_orden": "ORD-001"
        })
        
        assert result is False

    @patch.dict("os.environ", {"PUBSUB_EMULATOR_HOST": "localhost:8085"})
    @patch("services.pubsub_service.pubsub_v1.PublisherClient")
    def test_publish_event_publish_fails(self, mock_publisher_class):
        """Test handling of publish failure"""
        mock_publisher_instance = Mock()
        mock_publisher_instance.topic_path.return_value = "projects/test-project/topics/order-projection-created"
        mock_publisher_instance.publish.side_effect = Exception("Network error")
        mock_publisher_class.return_value = mock_publisher_instance
        
        service = PubSubService(project_id="test-project")
        
        result = service.publish_projection_created_event({
            "id": "order-123",
            "id_cliente": "client-456",
            "numero_orden": "ORD-001"
        })
        
        assert result is False

    @patch.dict("os.environ", {"PUBSUB_EMULATOR_HOST": "localhost:8085"})
    @patch("services.pubsub_service.pubsub_v1.PublisherClient")
    def test_publish_event_handles_datetime_serialization(self, mock_publisher_class, mock_future):
        """Test that event with datetime fields is properly serialized"""
        from datetime import datetime
        
        mock_publisher_instance = Mock()
        mock_publisher_instance.topic_path.return_value = "projects/test-project/topics/order-projection-created"
        mock_publisher_instance.publish.return_value = mock_future
        mock_publisher_class.return_value = mock_publisher_instance
        
        service = PubSubService(project_id="test-project")
        
        projection_data = {
            "id": "order-123",
            "id_cliente": "client-456",
            "numero_orden": "ORD-001",
            "fecha_creacion": datetime(2024, 1, 1, 12, 0, 0)
        }
        
        result = service.publish_projection_created_event(projection_data)
        
        assert result is True
        # Should not raise JSON serialization error


class TestCheckTopicExists:
    """Tests for check_topic_exists method"""

    @patch.dict("os.environ", {"PUBSUB_EMULATOR_HOST": "localhost:8085"})
    @patch("services.pubsub_service.pubsub_v1.PublisherClient")
    def test_topic_exists(self, mock_publisher_class):
        """Test checking if topic exists"""
        mock_publisher_instance = Mock()
        mock_publisher_instance.topic_path.return_value = "projects/test-project/topics/order-projection-created"
        mock_publisher_instance.get_topic.return_value = Mock()
        mock_publisher_class.return_value = mock_publisher_instance
        
        service = PubSubService(project_id="test-project")
        
        result = service.check_topic_exists()
        
        assert result is True
        mock_publisher_instance.get_topic.assert_called_once()

    @patch.dict("os.environ", {"PUBSUB_EMULATOR_HOST": "localhost:8085"})
    @patch("services.pubsub_service.pubsub_v1.PublisherClient")
    def test_topic_does_not_exist(self, mock_publisher_class):
        """Test checking when topic doesn't exist"""
        mock_publisher_instance = Mock()
        mock_publisher_instance.topic_path.return_value = "projects/test-project/topics/order-projection-created"
        mock_publisher_instance.get_topic.side_effect = Exception("Topic not found")
        mock_publisher_class.return_value = mock_publisher_instance
        
        service = PubSubService(project_id="test-project")
        
        result = service.check_topic_exists()
        
        assert result is False

    @patch.dict("os.environ", {"PUBSUB_EMULATOR_HOST": "localhost:8085"})
    @patch("services.pubsub_service.pubsub_v1.PublisherClient")
    def test_topic_check_no_publisher(self, mock_publisher_class):
        """Test topic check when publisher is not initialized"""
        service = PubSubService(project_id="test-project")
        service._publisher = None
        
        result = service.check_topic_exists()
        
        assert result is False


class TestGetPubSubService:
    """Tests for get_pubsub_service factory function"""

    @patch.dict("os.environ", {"PUBSUB_EMULATOR_HOST": "localhost:8085"})
    @patch("services.pubsub_service.pubsub_v1.PublisherClient")
    def test_get_pubsub_service_returns_instance(self, mock_publisher_class):
        """Test that factory function returns PubSubService instance"""
        from services.pubsub_service import get_pubsub_service
        
        service = get_pubsub_service()
        
        assert isinstance(service, PubSubService)
        assert service._publisher is not None

