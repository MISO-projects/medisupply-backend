import pytest
import os
from unittest.mock import Mock, patch, MagicMock
from services.pubsub_service import PubSubService, DateTimeEncoder
from datetime import datetime, date
import json


class TestDateTimeEncoder:
    """Tests para el encoder personalizado de JSON"""

    def test_encode_datetime(self):
        # Arrange
        dt = datetime(2025, 10, 30, 10, 30, 0)
        
        # Act
        result = json.dumps({"fecha": dt}, cls=DateTimeEncoder)
        
        # Assert
        assert "2025-10-30T10:30:00" in result
    
    def test_encode_date(self):
        # Arrange
        d = date(2025, 10, 30)
        
        # Act
        result = json.dumps({"fecha": d}, cls=DateTimeEncoder)
        
        # Assert
        assert "2025-10-30" in result
    
    def test_encode_regular_data(self):
        # Arrange
        data = {"nombre": "Test", "valor": 123}
        
        # Act
        result = json.dumps(data, cls=DateTimeEncoder)
        
        # Assert
        assert "Test" in result
        assert "123" in result


class TestPubSubService:
    """Tests para el servicio de PubSub"""

    @patch('services.pubsub_service.Credentials')
    @patch('services.pubsub_service.pubsub_v1.PublisherClient')
    @patch('services.pubsub_service.os.path.exists')
    def test_init_con_archivo_credenciales(self, mock_exists, mock_publisher, mock_credentials):
        # Arrange
        mock_exists.return_value = True
        mock_credentials.from_service_account_file.return_value = Mock()
        os.environ["GOOGLE_CLOUD_PROJECT_ID"] = "test-project"
        os.environ["PUBSUB_TOPIC_NAME"] = "test-topic"
        
        # Act
        service = PubSubService()
        
        # Assert
        assert service.project_id == "test-project"
        assert service.topic_name == "test-topic"
        mock_credentials.from_service_account_file.assert_called_once_with("credentials.json")
        mock_publisher.assert_called_once()
    
    @patch('services.pubsub_service.default')
    @patch('services.pubsub_service.pubsub_v1.PublisherClient')
    @patch('services.pubsub_service.os.path.exists')
    def test_init_con_credenciales_default(self, mock_exists, mock_publisher, mock_default):
        # Arrange
        mock_exists.return_value = False
        mock_default.return_value = (Mock(), "default-project")
        os.environ["GOOGLE_CLOUD_PROJECT_ID"] = ""
        os.environ["PUBSUB_TOPIC_NAME"] = "test-topic"
        
        # Act
        service = PubSubService()
        
        # Assert
        assert service.project_id == "default-project"
        assert service.topic_name == "test-topic"
        mock_default.assert_called_once()
        mock_publisher.assert_called_once()
    
    @patch('services.pubsub_service.default')
    @patch('services.pubsub_service.pubsub_v1.PublisherClient')
    @patch('services.pubsub_service.os.path.exists')
    def test_init_fallo_credenciales(self, mock_exists, mock_publisher, mock_default):
        # Arrange
        mock_exists.return_value = False
        mock_default.side_effect = Exception("Error de autenticación")
        
        # Act - El servicio debe inicializarse sin lanzar excepción (degradación elegante)
        service = PubSubService()
        
        # Assert - El publisher debe ser None debido al fallo de credenciales
        assert service._publisher is None
        # El servicio está inicializado aunque no pueda publicar eventos
        assert isinstance(service, PubSubService)
    
    @patch('services.pubsub_service.Credentials')
    @patch('services.pubsub_service.pubsub_v1.PublisherClient')
    @patch('services.pubsub_service.os.path.exists')
    def test_publish_event_exitoso(self, mock_exists, mock_publisher_class, mock_credentials):
        # Arrange
        mock_exists.return_value = True
        mock_credentials.from_service_account_file.return_value = Mock()
        
        mock_publisher = Mock()
        mock_future = Mock()
        mock_future.result.return_value = "message-id-123"
        mock_publisher.publish.return_value = mock_future
        mock_publisher.topic_path.return_value = "projects/test-project/topics/test-topic"
        mock_publisher_class.return_value = mock_publisher
        
        os.environ["GOOGLE_CLOUD_PROJECT_ID"] = "test-project"
        os.environ["PUBSUB_TOPIC_NAME"] = "test-topic"
        
        service = PubSubService()
        
        event_data = {
            "tipo": "ruta_creada",
            "ruta_id": 123,
            "fecha": datetime(2025, 10, 30, 10, 30, 0)
        }
        
        # Act
        resultado = service.publish_event(event_data)
        
        # Assert
        assert resultado is True
        mock_publisher.publish.assert_called_once()
        mock_publisher.topic_path.assert_called_once_with("test-project", "test-topic")
    
    @patch('services.pubsub_service.Credentials')
    @patch('services.pubsub_service.pubsub_v1.PublisherClient')
    @patch('services.pubsub_service.os.path.exists')
    def test_publish_event_fallo(self, mock_exists, mock_publisher_class, mock_credentials):
        # Arrange
        mock_exists.return_value = True
        mock_credentials.from_service_account_file.return_value = Mock()
        
        mock_publisher = Mock()
        mock_publisher.publish.side_effect = Exception("Error al publicar")
        mock_publisher.topic_path.return_value = "projects/test-project/topics/test-topic"
        mock_publisher_class.return_value = mock_publisher
        
        os.environ["GOOGLE_CLOUD_PROJECT_ID"] = "test-project"
        os.environ["PUBSUB_TOPIC_NAME"] = "test-topic"
        
        service = PubSubService()
        
        event_data = {"tipo": "test"}
        
        # Act
        resultado = service.publish_event(event_data)
        
        # Assert
        assert resultado is False
    
    @patch('services.pubsub_service.Credentials')
    @patch('services.pubsub_service.pubsub_v1.PublisherClient')
    @patch('services.pubsub_service.os.path.exists')
    def test_publish_event_sin_cliente_inicializado(self, mock_exists, mock_publisher_class, mock_credentials):
        # Arrange
        mock_exists.return_value = True
        mock_credentials.from_service_account_file.return_value = Mock()
        mock_publisher_class.return_value = Mock()
        
        os.environ["GOOGLE_CLOUD_PROJECT_ID"] = "test-project"
        os.environ["PUBSUB_TOPIC_NAME"] = "test-topic"
        
        service = PubSubService()
        service._publisher = None
        
        event_data = {"tipo": "test"}
        
        # Act
        resultado = service.publish_event(event_data)
        
        # Assert
        assert resultado is False
    
    @patch('services.pubsub_service.Credentials')
    @patch('services.pubsub_service.pubsub_v1.PublisherClient')
    @patch('services.pubsub_service.os.path.exists')
    def test_check_topic_exists_exitoso(self, mock_exists, mock_publisher_class, mock_credentials):
        # Arrange
        mock_exists.return_value = True
        mock_credentials.from_service_account_file.return_value = Mock()
        
        mock_publisher = Mock()
        mock_publisher.get_topic.return_value = Mock()
        mock_publisher.topic_path.return_value = "projects/test-project/topics/test-topic"
        mock_publisher_class.return_value = mock_publisher
        
        os.environ["GOOGLE_CLOUD_PROJECT_ID"] = "test-project"
        os.environ["PUBSUB_TOPIC_NAME"] = "test-topic"
        
        service = PubSubService()
        
        # Act
        resultado = service.check_topic_exists()
        
        # Assert
        assert resultado is True
        mock_publisher.get_topic.assert_called_once()
    
    @patch('services.pubsub_service.Credentials')
    @patch('services.pubsub_service.pubsub_v1.PublisherClient')
    @patch('services.pubsub_service.os.path.exists')
    def test_check_topic_exists_no_existe(self, mock_exists, mock_publisher_class, mock_credentials):
        # Arrange
        mock_exists.return_value = True
        mock_credentials.from_service_account_file.return_value = Mock()
        
        mock_publisher = Mock()
        mock_publisher.get_topic.side_effect = Exception("Topic not found")
        mock_publisher.topic_path.return_value = "projects/test-project/topics/test-topic"
        mock_publisher_class.return_value = mock_publisher
        
        os.environ["GOOGLE_CLOUD_PROJECT_ID"] = "test-project"
        os.environ["PUBSUB_TOPIC_NAME"] = "test-topic"
        
        service = PubSubService()
        
        # Act
        resultado = service.check_topic_exists()
        
        # Assert
        assert resultado is False
    
    @patch('services.pubsub_service.Credentials')
    @patch('services.pubsub_service.pubsub_v1.PublisherClient')
    @patch('services.pubsub_service.os.path.exists')
    def test_get_pubsub_service(self, mock_exists, mock_publisher_class, mock_credentials):
        # Arrange
        mock_exists.return_value = True
        mock_credentials.from_service_account_file.return_value = Mock()
        mock_publisher_class.return_value = Mock()
        
        os.environ["GOOGLE_CLOUD_PROJECT_ID"] = "test-project"
        os.environ["PUBSUB_TOPIC_NAME"] = "test-topic"
        
        # Act
        from services.pubsub_service import get_pubsub_service
        service = get_pubsub_service()
        
        # Assert
        assert isinstance(service, PubSubService)
    
    @patch('services.pubsub_service.Credentials')
    @patch('services.pubsub_service.pubsub_v1.PublisherClient')
    @patch('services.pubsub_service.os.path.exists')
    def test_publish_event_con_datos_complejos(self, mock_exists, mock_publisher_class, mock_credentials):
        # Arrange
        mock_exists.return_value = True
        mock_credentials.from_service_account_file.return_value = Mock()
        
        mock_publisher = Mock()
        mock_future = Mock()
        mock_future.result.return_value = "message-id-123"
        mock_publisher.publish.return_value = mock_future
        mock_publisher.topic_path.return_value = "projects/test-project/topics/test-topic"
        mock_publisher_class.return_value = mock_publisher
        
        os.environ["GOOGLE_CLOUD_PROJECT_ID"] = "test-project"
        os.environ["PUBSUB_TOPIC_NAME"] = "test-topic"
        
        service = PubSubService()
        
        event_data = {
            "tipo": "ruta_creada",
            "ruta_id": 123,
            "fecha": datetime(2025, 10, 30, 10, 30, 0),
            "paradas": [
                {"id": 1, "direccion": "Calle 1"},
                {"id": 2, "direccion": "Calle 2"}
            ],
            "conductor": {
                "id": 1,
                "nombre": "Juan Pérez"
            }
        }
        
        # Act
        resultado = service.publish_event(event_data)
        
        # Assert
        assert resultado is True
        mock_publisher.publish.assert_called_once()
        
        # Verificar que los datos se serializaron correctamente
        call_args = mock_publisher.publish.call_args
        message_bytes = call_args[0][1]
        message_str = message_bytes.decode("utf-8")
        assert "ruta_creada" in message_str
        assert "2025-10-30T10:30:00" in message_str

