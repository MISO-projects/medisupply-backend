import pytest
from unittest.mock import Mock, MagicMock, patch
from fastapi import HTTPException
from services.order_projection_handler import OrderProjectionHandler
from db.order_projection_model import OrderProjection


@pytest.fixture
def mock_db():
    """Mock database session"""
    db = Mock()
    db.add = Mock()
    db.commit = Mock()
    db.refresh = Mock()
    return db


@pytest.fixture
def mock_pubsub_service():
    """Mock PubSubService"""
    service = Mock()
    service.publish_projection_created_event = Mock(return_value=True)
    return service


@pytest.fixture
def sample_event_data():
    """Sample order event data"""
    import uuid
    from datetime import datetime
    return {
        "id": str(uuid.uuid4()),
        "numero_orden": "ORD-2024-001",
        "id_cliente": str(uuid.uuid4()),
        "id_vendedor": str(uuid.uuid4()),
        "creado_por": str(uuid.uuid4()),
        "estado": "PENDING",
        "observaciones": "Test order",
        "fecha_creacion": "2024-01-01T10:00:00",
        "fecha_actualizacion": "2024-01-01T10:00:00",
        "fecha_entrega_estimada": "2024-01-10T10:00:00",
        "valor_total": 500.0,
        "detalles": [
            {
                "id_producto": "prod-1",
                "nombre_producto": "Product A",
                "cantidad": 10,
                "precio_unitario": 50.0
            }
        ]
    }


class TestOrderProjectionHandler:
    """Tests for OrderProjectionHandler"""

    def test_handle_order_created_event_success(
        self, mock_db, mock_pubsub_service, sample_event_data
    ):
        """Test successful handling of order created event"""
        with patch("services.order_projection_handler.PubSubService", return_value=mock_pubsub_service):
            handler = OrderProjectionHandler(db=mock_db)
            
            with patch.object(OrderProjection, "to_dict", return_value=sample_event_data):
                result = handler.handle_order_created_event(sample_event_data)
            
            # Verify database operations
            mock_db.add.assert_called_once()
            mock_db.commit.assert_called_once()
            mock_db.refresh.assert_called_once()
            
            # Verify event publishing
            mock_pubsub_service.publish_projection_created_event.assert_called_once()
            
            # Verify result
            assert result == sample_event_data

    def test_handle_order_created_event_publishes_correct_data(
        self, mock_db, mock_pubsub_service, sample_event_data
    ):
        """Test that handler publishes correct projection data"""
        with patch("services.order_projection_handler.PubSubService", return_value=mock_pubsub_service):
            handler = OrderProjectionHandler(db=mock_db)
            
            with patch.object(OrderProjection, "to_dict", return_value=sample_event_data):
                handler.handle_order_created_event(sample_event_data)
            
            # Verify publish was called with projection dict
            call_args = mock_pubsub_service.publish_projection_created_event.call_args
            assert call_args[0][0] == sample_event_data

    def test_handle_order_created_event_database_error(
        self, mock_db, mock_pubsub_service, sample_event_data
    ):
        """Test handling of database errors"""
        mock_db.commit.side_effect = Exception("Database error")
        
        with patch("services.order_projection_handler.PubSubService", return_value=mock_pubsub_service):
            handler = OrderProjectionHandler(db=mock_db)
            
            with pytest.raises(HTTPException) as exc_info:
                handler.handle_order_created_event(sample_event_data)
            
            assert exc_info.value.status_code == 400
            assert "Error creating projection" in exc_info.value.detail
            
            # Event should not be published if projection creation fails
            mock_pubsub_service.publish_projection_created_event.assert_not_called()

    def test_handle_order_created_event_publish_fails_gracefully(
        self, mock_db, mock_pubsub_service, sample_event_data
    ):
        """Test that projection succeeds even if event publishing fails"""
        mock_pubsub_service.publish_projection_created_event.return_value = False
        
        with patch("services.order_projection_handler.PubSubService", return_value=mock_pubsub_service):
            handler = OrderProjectionHandler(db=mock_db)
            
            with patch.object(OrderProjection, "to_dict", return_value=sample_event_data):
                result = handler.handle_order_created_event(sample_event_data)
            
            # Projection should still be created
            mock_db.add.assert_called_once()
            mock_db.commit.assert_called_once()
            assert result == sample_event_data
            
            # Verify publish was attempted
            mock_pubsub_service.publish_projection_created_event.assert_called_once()

    def test_handle_order_created_event_publish_exception_gracefully(
        self, mock_db, mock_pubsub_service, sample_event_data
    ):
        """Test that projection succeeds even if event publishing raises exception"""
        mock_pubsub_service.publish_projection_created_event.side_effect = Exception("Pub/Sub error")
        
        with patch("services.order_projection_handler.PubSubService", return_value=mock_pubsub_service):
            handler = OrderProjectionHandler(db=mock_db)
            
            with patch.object(OrderProjection, "to_dict", return_value=sample_event_data):
                # Should not raise exception
                result = handler.handle_order_created_event(sample_event_data)
            
            # Projection should still be created
            mock_db.add.assert_called_once()
            mock_db.commit.assert_called_once()
            assert result == sample_event_data

    def test_publish_projection_created_event_success(
        self, mock_db, mock_pubsub_service, sample_event_data
    ):
        """Test _publish_projection_created_event method"""
        with patch("services.order_projection_handler.PubSubService", return_value=mock_pubsub_service):
            handler = OrderProjectionHandler(db=mock_db)
            
            # Create a mock projection
            mock_projection = Mock()
            mock_projection.numero_orden = "ORD-2024-001"
            mock_projection.to_dict.return_value = sample_event_data
            
            handler._publish_projection_created_event(mock_projection)
            
            # Verify publish was called
            mock_pubsub_service.publish_projection_created_event.assert_called_once_with(
                sample_event_data
            )

    def test_publish_projection_created_event_logs_on_failure(
        self, mock_db, mock_pubsub_service, sample_event_data
    ):
        """Test that event publishing failure is logged but doesn't raise"""
        mock_pubsub_service.publish_projection_created_event.return_value = False
        
        with patch("services.order_projection_handler.PubSubService", return_value=mock_pubsub_service):
            with patch("services.order_projection_handler.logger") as mock_logger:
                handler = OrderProjectionHandler(db=mock_db)
                
                mock_projection = Mock()
                mock_projection.numero_orden = "ORD-2024-001"
                mock_projection.to_dict.return_value = sample_event_data
                
                # Should not raise exception
                handler._publish_projection_created_event(mock_projection)
                
                # Verify warning was logged
                assert mock_logger.warning.called

    def test_multiple_events_handled_correctly(
        self, mock_db, mock_pubsub_service
    ):
        """Test handling multiple events sequentially"""
        import uuid
        
        with patch("services.order_projection_handler.PubSubService", return_value=mock_pubsub_service):
            handler = OrderProjectionHandler(db=mock_db)
            
            events = [
                {
                    "id": str(uuid.uuid4()),
                    "numero_orden": f"ORD-{i}",
                    "id_cliente": str(uuid.uuid4()),
                    "id_vendedor": str(uuid.uuid4()),
                    "creado_por": str(uuid.uuid4()),
                    "estado": "PENDING",
                    "valor_total": 100.0 * (i + 1),
                    "fecha_creacion": "2024-01-01T10:00:00",
                    "fecha_actualizacion": "2024-01-01T10:00:00",
                    "fecha_entrega_estimada": "2024-01-10T10:00:00",
                    "detalles": []
                }
                for i in range(3)
            ]
            
            for event_data in events:
                with patch.object(OrderProjection, "to_dict", return_value=event_data):
                    handler.handle_order_created_event(event_data)
            
            # Verify all events were processed
            assert mock_db.add.call_count == 3
            assert mock_db.commit.call_count == 3
            assert mock_pubsub_service.publish_projection_created_event.call_count == 3

    def test_handler_initialization(self, mock_db):
        """Test proper initialization of OrderProjectionHandler"""
        with patch("services.order_projection_handler.PubSubService") as mock_pubsub_class:
            handler = OrderProjectionHandler(db=mock_db)
            
            assert handler.db == mock_db
            assert handler.pubsub_service is not None
            mock_pubsub_class.assert_called_once()

    def test_projection_data_includes_all_details(
        self, mock_db, mock_pubsub_service, sample_event_data
    ):
        """Test that projection includes all order details"""
        with patch("services.order_projection_handler.PubSubService", return_value=mock_pubsub_service):
            handler = OrderProjectionHandler(db=mock_db)
            
            # Verify OrderProjection is created with full event data
            with patch("services.order_projection_handler.OrderProjection") as mock_projection_class:
                mock_projection_instance = Mock()
                mock_projection_instance.numero_orden = "ORD-2024-001"
                mock_projection_instance.to_dict.return_value = sample_event_data
                mock_projection_class.return_value = mock_projection_instance
                
                handler.handle_order_created_event(sample_event_data)
                
                # Verify OrderProjection was instantiated with event data
                mock_projection_class.assert_called_once_with(sample_event_data)

    def test_event_with_minimal_data(self, mock_db, mock_pubsub_service):
        """Test handling event with minimal required data"""
        import uuid
        
        minimal_event_data = {
            "id": str(uuid.uuid4()),
            "numero_orden": "ORD-MIN-001",
            "id_cliente": str(uuid.uuid4()),
            "id_vendedor": str(uuid.uuid4()),
            "creado_por": str(uuid.uuid4()),
            "estado": "PENDING",
            "valor_total": 50.0,
            "fecha_creacion": "2024-01-01T10:00:00",
            "fecha_actualizacion": "2024-01-01T10:00:00",
            "fecha_entrega_estimada": "2024-01-10T10:00:00",
            "detalles": []
        }
        
        with patch("services.order_projection_handler.PubSubService", return_value=mock_pubsub_service):
            handler = OrderProjectionHandler(db=mock_db)
            
            with patch.object(OrderProjection, "to_dict", return_value=minimal_event_data):
                result = handler.handle_order_created_event(minimal_event_data)
            
            # Should still succeed
            mock_db.add.assert_called_once()
            mock_db.commit.assert_called_once()
            mock_pubsub_service.publish_projection_created_event.assert_called_once()
            assert result == minimal_event_data

