import pytest
from unittest.mock import Mock, patch, MagicMock
import json
from datetime import datetime
import uuid

from services.pubsub_service import PubSubService, DateTimeEncoder


class TestDateTimeEncoder:
    """Basic tests for DateTimeEncoder"""

    def test_datetime_encoding(self):
        """Test that datetime objects are encoded as ISO format strings"""
        encoder = DateTimeEncoder()
        dt = datetime(2024, 1, 15, 10, 30, 0)
        result = encoder.default(dt)
        assert result == "2024-01-15T10:30:00"

    def test_regular_objects_not_affected(self):
        """Test that non-datetime objects raise TypeError"""
        encoder = DateTimeEncoder()
        with pytest.raises(TypeError):
            encoder.default({"key": "value"})


class TestPubSubService:
    """Basic tests for PubSubService"""

    @pytest.fixture
    def mock_publisher(self):
        """Mock Pub/Sub publisher client"""
        publisher = Mock()
        publisher.topic_path = Mock(return_value="projects/test-project/topics/test-topic")
        
        # Mock the future returned by publish
        future = Mock()
        future.result = Mock(return_value="test-message-id-123")
        publisher.publish = Mock(return_value=future)
        
        return publisher

    @pytest.fixture
    def sample_order_data(self):
        """Sample order data for testing"""
        return {
            "id": str(uuid.uuid4()),
            "numero_orden": "ORD-250101-ABCD1234",
            "id_cliente": str(uuid.uuid4()),
            "id_vendedor": str(uuid.uuid4()),
            "creado_por": str(uuid.uuid4()),
            "observaciones": "Test order",
            "detalles": [
                {
                    "id_producto": str(uuid.uuid4()),
                    "cantidad": 5,
                    "precio_unitario": 100.0
                }
            ]
        }

    @patch('services.pubsub_service.pubsub_v1.PublisherClient')
    @patch.dict('os.environ', {'PUBSUB_EMULATOR_HOST': 'localhost:8085'})
    def test_initialization_with_emulator(self, mock_publisher_class):
        """Test PubSubService initialization with emulator"""
        mock_publisher = Mock()
        mock_publisher_class.return_value = mock_publisher
        
        service = PubSubService(project_id="test-project", topic_name="test-topic")
        
        assert service.project_id == "test-project"
        assert service.topic_name == "test-topic"
        mock_publisher_class.assert_called_once()

    @patch('services.pubsub_service.pubsub_v1.PublisherClient')
    @patch.dict('os.environ', {'GOOGLE_CLOUD_PROJECT_ID': 'env-project'})
    def test_initialization_uses_env_variables(self, mock_publisher_class):
        """Test that service uses environment variables when not provided"""
        mock_publisher = Mock()
        mock_publisher_class.return_value = mock_publisher
        
        with patch.dict('os.environ', {'PUBSUB_EMULATOR_HOST': 'localhost:8085'}):
            service = PubSubService()
        
        assert service.project_id == "env-project"
        assert service.topic_name == "create-order-command"  # default value

    @patch('services.pubsub_service.pubsub_v1.PublisherClient')
    @patch.dict('os.environ', {'PUBSUB_EMULATOR_HOST': 'localhost:8085'})
    def test_publish_create_order_command_success(
        self,
        mock_publisher_class,
        mock_publisher,
        sample_order_data
    ):
        """Test successful publishing of create order command"""
        mock_publisher_class.return_value = mock_publisher
        
        service = PubSubService(project_id="test-project", topic_name="test-topic")
        service._publisher = mock_publisher
        
        result = service.publish_create_order_command(sample_order_data)
        
        assert result is True
        mock_publisher.publish.assert_called_once()
        
        # Verify the message was properly encoded
        call_args = mock_publisher.publish.call_args
        topic_path = call_args[0][0]
        message_bytes = call_args[0][1]
        
        assert topic_path == "projects/test-project/topics/test-topic"
        
        # Verify message can be decoded
        message_json = message_bytes.decode("utf-8")
        message_data = json.loads(message_json)
        assert message_data["numero_orden"] == sample_order_data["numero_orden"]

    @patch('services.pubsub_service.pubsub_v1.PublisherClient')
    @patch.dict('os.environ', {'PUBSUB_EMULATOR_HOST': 'localhost:8085'})
    def test_publish_create_order_command_with_datetime(self, mock_publisher_class, mock_publisher):
        """Test publishing with datetime objects"""
        mock_publisher_class.return_value = mock_publisher
        
        service = PubSubService(project_id="test-project")
        service._publisher = mock_publisher
        
        order_data = {
            "id": str(uuid.uuid4()),
            "created_at": datetime(2024, 1, 15, 10, 30, 0)
        }
        
        result = service.publish_create_order_command(order_data)
        
        assert result is True
        
        # Verify datetime was properly serialized
        call_args = mock_publisher.publish.call_args
        message_bytes = call_args[0][1]
        message_data = json.loads(message_bytes.decode("utf-8"))
        assert message_data["created_at"] == "2024-01-15T10:30:00"

    @patch('services.pubsub_service.pubsub_v1.PublisherClient')
    @patch.dict('os.environ', {'PUBSUB_EMULATOR_HOST': 'localhost:8085'})
    def test_publish_create_order_command_failure(
        self,
        mock_publisher_class,
        sample_order_data
    ):
        """Test handling of publish failures"""
        mock_publisher = Mock()
        mock_publisher.topic_path = Mock(return_value="projects/test-project/topics/test-topic")
        mock_publisher.publish.side_effect = Exception("Publish error")
        mock_publisher_class.return_value = mock_publisher
        
        service = PubSubService(project_id="test-project")
        service._publisher = mock_publisher
        
        result = service.publish_create_order_command(sample_order_data)
        
        assert result is False

    @patch('services.pubsub_service.pubsub_v1.PublisherClient')
    @patch.dict('os.environ', {'PUBSUB_EMULATOR_HOST': 'localhost:8085'})
    def test_publish_without_publisher(self, mock_publisher_class, sample_order_data):
        """Test publishing when publisher is not initialized"""
        mock_publisher_class.return_value = Mock()
        
        service = PubSubService(project_id="test-project")
        service._publisher = None
        
        result = service.publish_create_order_command(sample_order_data)
        
        assert result is False

    @patch('services.pubsub_service.pubsub_v1.PublisherClient')
    @patch.dict('os.environ', {'PUBSUB_EMULATOR_HOST': 'localhost:8085'})
    def test_check_topic_exists_success(self, mock_publisher_class, mock_publisher):
        """Test checking if topic exists - success case"""
        mock_publisher.get_topic = Mock(return_value={"name": "test-topic"})
        mock_publisher_class.return_value = mock_publisher
        
        service = PubSubService(project_id="test-project", topic_name="test-topic")
        service._publisher = mock_publisher
        
        result = service.check_topic_exists()
        
        assert result is True
        mock_publisher.get_topic.assert_called_once()

    @patch('services.pubsub_service.pubsub_v1.PublisherClient')
    @patch.dict('os.environ', {'PUBSUB_EMULATOR_HOST': 'localhost:8085'})
    def test_check_topic_exists_failure(self, mock_publisher_class):
        """Test checking if topic exists - failure case"""
        mock_publisher = Mock()
        mock_publisher.topic_path = Mock(return_value="projects/test-project/topics/test-topic")
        mock_publisher.get_topic = Mock(side_effect=Exception("Topic not found"))
        mock_publisher_class.return_value = mock_publisher
        
        service = PubSubService(project_id="test-project", topic_name="test-topic")
        service._publisher = mock_publisher
        
        result = service.check_topic_exists()
        
        assert result is False

    @patch('services.pubsub_service.pubsub_v1.PublisherClient')
    @patch.dict('os.environ', {'PUBSUB_EMULATOR_HOST': 'localhost:8085'})
    def test_check_topic_without_publisher(self, mock_publisher_class):
        """Test checking topic when publisher is not initialized"""
        mock_publisher_class.return_value = Mock()
        
        service = PubSubService(project_id="test-project")
        service._publisher = None
        
        result = service.check_topic_exists()
        
        assert result is False

