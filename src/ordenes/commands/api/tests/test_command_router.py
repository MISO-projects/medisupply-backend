import pytest
from unittest.mock import Mock, patch, AsyncMock
from fastapi import HTTPException
import uuid

from services.order_service import OrderService
from schemas.orden_schema import CrearOrdenSchema, CrearOrdenClienteSchema


class TestCommandRouter:
    """Basic tests for command order router"""

    @pytest.fixture
    def mock_order_service(self):
        """Mock OrderService"""
        service = Mock(spec=OrderService)
        order_id = uuid.uuid4()
        service.create_order.return_value = {
            "id": order_id,
            "numero_orden": "ORD-250101-ABCD1234"
        }
        return service

    @pytest.fixture
    def sample_order_schema(self):
        """Sample order schema for testing"""
        return CrearOrdenSchema(
            id_cliente=uuid.uuid4(),
            id_vendedor=uuid.uuid4(),
            observaciones="Test order",
            detalles=[
                {
                    "id_producto": uuid.uuid4(),
                    "cantidad": 5,
                    "precio_unitario": 100.0,
                    "observaciones": "Product 1"
                }
            ]
        )

    @pytest.fixture
    def sample_client_order_schema(self):
        """Sample client order schema (without id_cliente)"""
        return CrearOrdenClienteSchema(
            id_vendedor=uuid.uuid4(),
            observaciones="Test client order",
            detalles=[
                {
                    "id_producto": uuid.uuid4(),
                    "cantidad": 3,
                    "precio_unitario": 50.0
                }
            ]
        )

    @pytest.mark.asyncio
    async def test_create_order_adds_user_id(self, mock_order_service, sample_order_schema):
        """Test that create_order adds creado_por from user token"""
        from router.command_ordenes import create_order
        
        user_id = str(uuid.uuid4())
        
        result = await create_order(
            order=sample_order_schema,
            order_service=mock_order_service,
            user_id=user_id
        )
        
        # Verify result structure
        assert "id" in result
        assert "numero_orden" in result
        
        # Verify creado_por was added to order data
        call_args = mock_order_service.create_order.call_args[0][0]
        assert call_args["creado_por"] == user_id

    @pytest.mark.asyncio
    async def test_create_order_calls_service(self, mock_order_service, sample_order_schema):
        """Test that create_order calls the order service"""
        from router.command_ordenes import create_order
        
        user_id = str(uuid.uuid4())
        
        await create_order(
            order=sample_order_schema,
            order_service=mock_order_service,
            user_id=user_id
        )
        
        # Verify service was called
        mock_order_service.create_order.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_client_order_adds_client_id(
        self,
        mock_order_service,
        sample_client_order_schema
    ):
        """Test that create_client_order adds id_cliente from client token"""
        from router.command_ordenes import create_client_order
        
        client_id = str(uuid.uuid4())
        
        result = await create_client_order(
            order=sample_client_order_schema,
            order_service=mock_order_service,
            client_id=client_id
        )
        
        # Verify result structure
        assert "id" in result
        assert "numero_orden" in result
        
        # Verify id_cliente was added to order data
        call_args = mock_order_service.create_order.call_args[0][0]
        assert call_args["id_cliente"] == client_id
        assert call_args["creado_por"] == client_id

    @pytest.mark.asyncio
    async def test_create_client_order_calls_service(
        self,
        mock_order_service,
        sample_client_order_schema
    ):
        """Test that create_client_order calls the order service"""
        from router.command_ordenes import create_client_order
        
        client_id = str(uuid.uuid4())
        
        await create_client_order(
            order=sample_client_order_schema,
            order_service=mock_order_service,
            client_id=client_id
        )
        
        # Verify service was called
        mock_order_service.create_order.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_order_preserves_order_data(
        self,
        mock_order_service,
        sample_order_schema
    ):
        """Test that create_order preserves original order data"""
        from router.command_ordenes import create_order
        
        user_id = str(uuid.uuid4())
        
        await create_order(
            order=sample_order_schema,
            order_service=mock_order_service,
            user_id=user_id
        )
        
        # Verify original data was preserved
        call_args = mock_order_service.create_order.call_args[0][0]
        assert str(call_args["id_cliente"]) == str(sample_order_schema.id_cliente)
        assert str(call_args["id_vendedor"]) == str(sample_order_schema.id_vendedor)
        assert call_args["observaciones"] == sample_order_schema.observaciones

    @pytest.mark.asyncio
    async def test_create_order_service_exception(self, sample_order_schema):
        """Test handling of service exceptions"""
        from router.command_ordenes import create_order
        
        mock_service = Mock(spec=OrderService)
        mock_service.create_order.side_effect = Exception("Service error")
        
        user_id = str(uuid.uuid4())
        
        # Should raise the exception
        with pytest.raises(Exception) as exc_info:
            await create_order(
                order=sample_order_schema,
                order_service=mock_service,
                user_id=user_id
            )
        
        assert "Service error" in str(exc_info.value)

