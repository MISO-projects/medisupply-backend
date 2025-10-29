import pytest
from unittest.mock import Mock, patch
import uuid
from datetime import datetime

from services.order_service import OrderService
from services.pubsub_service import PubSubService


class TestOrderService:
    """Basic tests for OrderService"""

    @pytest.fixture
    def mock_pubsub_service(self):
        """Mock PubSubService"""
        service = Mock(spec=PubSubService)
        service.publish_create_order_command = Mock(return_value=True)
        return service

    @pytest.fixture
    def order_service(self, mock_pubsub_service):
        """Create OrderService with mocked dependencies"""
        return OrderService(pubsub_service=mock_pubsub_service)

    @pytest.fixture
    def sample_order_data(self):
        """Sample order data for testing"""
        return {
            "id_cliente": str(uuid.uuid4()),
            "id_vendedor": str(uuid.uuid4()),
            "creado_por": str(uuid.uuid4()),
            "observaciones": "Test order",
            "detalles": [
                {
                    "id_producto": str(uuid.uuid4()),
                    "cantidad": 5,
                    "precio_unitario": 100.0,
                    "observaciones": "Product 1"
                }
            ]
        }

    def test_generar_numero_orden_format(self, order_service):
        """Test that generated order number has correct format"""
        numero_orden = order_service.generar_numero_orden()
        
        # Verify format: ORD-YYMMDD-XXXXXXXX
        assert numero_orden.startswith("ORD-")
        parts = numero_orden.split("-")
        assert len(parts) == 3
        assert parts[0] == "ORD"
        assert len(parts[1]) == 6  # YYMMDD
        assert len(parts[2]) == 8  # UUID part
        assert parts[2] == parts[2].upper()  # UUID part should be uppercase (no lowercase chars)

    def test_generar_numero_orden_unique(self, order_service):
        """Test that generated order numbers are unique"""
        numero_orden_1 = order_service.generar_numero_orden()
        numero_orden_2 = order_service.generar_numero_orden()
        
        # They should be different (UUID part makes them unique)
        assert numero_orden_1 != numero_orden_2

    def test_create_order_success(self, order_service, mock_pubsub_service, sample_order_data):
        """Test successful order creation"""
        result = order_service.create_order(sample_order_data)
        
        # Verify result structure
        assert "id" in result
        assert "numero_orden" in result
        assert isinstance(result["id"], uuid.UUID)
        assert result["numero_orden"].startswith("ORD-")
        
        # Verify pubsub was called
        mock_pubsub_service.publish_create_order_command.assert_called_once()
        
        # Verify order data was enriched with id and numero_orden
        call_args = mock_pubsub_service.publish_create_order_command.call_args[0][0]
        assert "id" in call_args
        assert "numero_orden" in call_args

    def test_create_order_adds_id(self, order_service, mock_pubsub_service, sample_order_data):
        """Test that create_order adds an ID to order data"""
        result = order_service.create_order(sample_order_data)
        
        # Verify ID was added to the order data
        call_args = mock_pubsub_service.publish_create_order_command.call_args[0][0]
        assert "id" in call_args
        assert call_args["id"] == str(result["id"])

    def test_create_order_adds_numero_orden(self, order_service, mock_pubsub_service, sample_order_data):
        """Test that create_order adds numero_orden to order data"""
        result = order_service.create_order(sample_order_data)
        
        # Verify numero_orden was added
        call_args = mock_pubsub_service.publish_create_order_command.call_args[0][0]
        assert "numero_orden" in call_args
        assert call_args["numero_orden"] == result["numero_orden"]

    def test_create_order_pubsub_failure(self, order_service, mock_pubsub_service, sample_order_data):
        """Test order creation fails when pubsub fails"""
        mock_pubsub_service.publish_create_order_command.return_value = False
        
        with pytest.raises(Exception) as exc_info:
            order_service.create_order(sample_order_data)
        
        assert "Failed to publish create order command" in str(exc_info.value)

    def test_create_order_preserves_original_data(self, order_service, mock_pubsub_service, sample_order_data):
        """Test that original order data is preserved"""
        original_cliente = sample_order_data["id_cliente"]
        original_vendedor = sample_order_data["id_vendedor"]
        original_observaciones = sample_order_data["observaciones"]
        
        order_service.create_order(sample_order_data)
        
        # Verify original data was preserved in the call
        call_args = mock_pubsub_service.publish_create_order_command.call_args[0][0]
        assert call_args["id_cliente"] == original_cliente
        assert call_args["id_vendedor"] == original_vendedor
        assert call_args["observaciones"] == original_observaciones

    @patch('services.order_service.PubSubService')
    def test_order_service_initialization_default(self, mock_pubsub_class):
        """Test OrderService can be initialized without parameters"""
        mock_pubsub_instance = Mock()
        mock_pubsub_class.return_value = mock_pubsub_instance
        
        service = OrderService()
        
        assert service.pubsub_service is not None
        mock_pubsub_class.assert_called_once()

    def test_order_service_initialization_with_pubsub(self, mock_pubsub_service):
        """Test OrderService can be initialized with custom pubsub service"""
        service = OrderService(pubsub_service=mock_pubsub_service)
        assert service.pubsub_service == mock_pubsub_service

