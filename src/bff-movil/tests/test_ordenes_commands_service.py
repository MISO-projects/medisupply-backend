import pytest
from unittest.mock import Mock, AsyncMock, patch
import httpx
from fastapi import HTTPException

from services.ordenes_commands_service import OrdenesCommandsService


class TestOrdenesCommandsService:
    
    @pytest.fixture
    def ordenes_commands_service(self):
        with patch.dict('os.environ', {'ORDENES_COMMANDS_SERVICE_URL': 'http://test-service:3000'}):
            return OrdenesCommandsService()
    
    @pytest.fixture
    def sample_order_data(self):
        return {
            "observaciones": "Orden de prueba",
            "id_cliente": "C001",
            "id_vendedor": "V001",
            "detalles": [
                {
                    "id_producto": "P001",
                    "cantidad": 10,
                    "precio_unitario": 15.50,
                    "observaciones": "Urgente"
                }
            ]
        }
    
    @pytest.fixture
    def sample_create_response(self):
        return {
            "id": "ORD-001",
            "numero_orden": "ORD-251025-A1B2C3D4"
        }

    def test_health_check_success(self, ordenes_commands_service):
        """Test exitoso para health check"""
        mock_response = Mock()
        mock_response.json.return_value = {"status": "healthy"}
        mock_response.raise_for_status.return_value = None
        
        with patch('httpx.get', return_value=mock_response) as mock_get:
            result = ordenes_commands_service.health_check()
            
            assert result == {"status": "healthy"}
            mock_get.assert_called_once_with("http://test-service:3000/health", timeout=30.0)

    def test_health_check_service_error(self, ordenes_commands_service):
        """Test para error del servicio"""
        with patch('httpx.get') as mock_get:
            mock_get.side_effect = httpx.HTTPStatusError("Service error", request=Mock(), response=Mock())
            
            with pytest.raises(HTTPException) as exc_info:
                ordenes_commands_service.health_check()
            
            assert exc_info.value.status_code == 503

    def test_health_check_connection_error(self, ordenes_commands_service):
        """Test para error de conexión"""
        with patch('httpx.get') as mock_get:
            mock_get.side_effect = httpx.RequestError("Connection error")
            
            with pytest.raises(HTTPException) as exc_info:
                ordenes_commands_service.health_check()
            
            assert exc_info.value.status_code == 503

    @pytest.mark.asyncio
    async def test_create_order_success(self, ordenes_commands_service, sample_order_data, sample_create_response):
        """Test exitoso para crear orden"""
        mock_response = Mock()
        mock_response.status_code = 201
        mock_response.json.return_value = sample_create_response
        mock_response.raise_for_status.return_value = None
        
        mock_client = AsyncMock()
        mock_client.__aenter__.return_value.post = AsyncMock(return_value=mock_response)
        mock_client.__aexit__.return_value = None
        
        with patch('httpx.AsyncClient', return_value=mock_client):
            result = await ordenes_commands_service.create_order(
                order_data=sample_order_data,
                authorization="Bearer test-token"
            )
            
            assert result == sample_create_response
            mock_client.__aenter__.return_value.post.assert_called_once()
            call_args = mock_client.__aenter__.return_value.post.call_args
            assert "/ordenes/" in call_args[0][0]
            assert call_args[1]["json"] == sample_order_data
            assert call_args[1]["headers"]["Authorization"] == "Bearer test-token"

    @pytest.mark.asyncio
    async def test_create_order_bad_request(self, ordenes_commands_service, sample_order_data):
        """Test para error de validación (400)"""
        mock_response = Mock()
        mock_response.status_code = 400
        mock_response.text = "Bad Request"
        mock_response.json.return_value = {"detail": "Datos inválidos"}
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "Bad Request", request=Mock(), response=mock_response
        )
        
        mock_client = AsyncMock()
        mock_client.__aenter__.return_value.post = AsyncMock(return_value=mock_response)
        
        with patch('httpx.AsyncClient', return_value=mock_client):
            with pytest.raises(HTTPException) as exc_info:
                await ordenes_commands_service.create_order(
                    order_data=sample_order_data,
                    authorization="Bearer test-token"
                )
            
            assert exc_info.value.status_code == 400
            assert "Datos inválidos" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_create_order_unauthorized(self, ordenes_commands_service, sample_order_data):
        """Test para token no autorizado (401)"""
        mock_response = Mock()
        mock_response.status_code = 401
        mock_response.text = "Unauthorized"
        mock_response.json.return_value = {"detail": "Token inválido"}
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "Unauthorized", request=Mock(), response=mock_response
        )
        
        mock_client = AsyncMock()
        mock_client.__aenter__.return_value.post = AsyncMock(return_value=mock_response)
        
        with patch('httpx.AsyncClient', return_value=mock_client):
            with pytest.raises(HTTPException) as exc_info:
                await ordenes_commands_service.create_order(
                    order_data=sample_order_data,
                    authorization="Bearer invalid-token"
                )
            
            assert exc_info.value.status_code == 401

    @pytest.mark.asyncio
    async def test_create_order_service_unavailable(self, ordenes_commands_service, sample_order_data):
        """Test para servicio no disponible"""
        mock_client = AsyncMock()
        mock_client.__aenter__.return_value.post = AsyncMock(
            side_effect=httpx.RequestError("Service unavailable")
        )
        
        with patch('httpx.AsyncClient', return_value=mock_client):
            with pytest.raises(HTTPException) as exc_info:
                await ordenes_commands_service.create_order(
                    order_data=sample_order_data,
                    authorization="Bearer test-token"
                )
            
            assert exc_info.value.status_code == 503
            assert "No se puede conectar al servicio de órdenes" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_create_client_order_success(self, ordenes_commands_service, sample_order_data, sample_create_response):
        """Test exitoso para crear orden de cliente"""
        # Remover id_cliente ya que se extrae del token
        order_data_cliente = sample_order_data.copy()
        del order_data_cliente["id_cliente"]
        
        mock_response = Mock()
        mock_response.status_code = 201
        mock_response.json.return_value = sample_create_response
        mock_response.raise_for_status.return_value = None
        
        mock_client = AsyncMock()
        mock_client.__aenter__.return_value.post = AsyncMock(return_value=mock_response)
        
        with patch('httpx.AsyncClient', return_value=mock_client):
            result = await ordenes_commands_service.create_client_order(
                order_data=order_data_cliente,
                authorization="Bearer test-token"
            )
            
            assert result == sample_create_response
            mock_client.__aenter__.return_value.post.assert_called_once()
            call_args = mock_client.__aenter__.return_value.post.call_args
            assert "/ordenes/cliente" in call_args[0][0]
            assert call_args[1]["json"] == order_data_cliente
            assert call_args[1]["headers"]["Authorization"] == "Bearer test-token"

    @pytest.mark.asyncio
    async def test_create_client_order_bad_request(self, ordenes_commands_service):
        """Test para error de validación en orden de cliente"""
        order_data = {
            "detalles": []  # Lista vacía debería causar error
        }
        
        mock_response = Mock()
        mock_response.status_code = 400
        mock_response.text = "Bad Request"
        mock_response.json.return_value = {"detail": "La orden debe tener al menos un detalle"}
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "Bad Request", request=Mock(), response=mock_response
        )
        
        mock_client = AsyncMock()
        mock_client.__aenter__.return_value.post = AsyncMock(return_value=mock_response)
        
        with patch('httpx.AsyncClient', return_value=mock_client):
            with pytest.raises(HTTPException) as exc_info:
                await ordenes_commands_service.create_client_order(
                    order_data=order_data,
                    authorization="Bearer test-token"
                )
            
            assert exc_info.value.status_code == 400

    @pytest.mark.asyncio
    async def test_create_client_order_forbidden(self, ordenes_commands_service, sample_order_data):
        """Test para acceso denegado en orden de cliente (403)"""
        order_data_cliente = sample_order_data.copy()
        del order_data_cliente["id_cliente"]
        
        mock_response = Mock()
        mock_response.status_code = 403
        mock_response.text = "Forbidden"
        mock_response.json.return_value = {"detail": "Acceso denegado"}
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "Forbidden", request=Mock(), response=mock_response
        )
        
        mock_client = AsyncMock()
        mock_client.__aenter__.return_value.post = AsyncMock(return_value=mock_response)
        
        with patch('httpx.AsyncClient', return_value=mock_client):
            with pytest.raises(HTTPException) as exc_info:
                await ordenes_commands_service.create_client_order(
                    order_data=order_data_cliente,
                    authorization="Bearer test-token"
                )
            
            assert exc_info.value.status_code == 403

    @pytest.mark.asyncio
    async def test_create_client_order_service_unavailable(self, ordenes_commands_service, sample_order_data):
        """Test para servicio no disponible en orden de cliente"""
        order_data_cliente = sample_order_data.copy()
        del order_data_cliente["id_cliente"]
        
        mock_client = AsyncMock()
        mock_client.__aenter__.return_value.post = AsyncMock(
            side_effect=httpx.RequestError("Service unavailable")
        )
        
        with patch('httpx.AsyncClient', return_value=mock_client):
            with pytest.raises(HTTPException) as exc_info:
                await ordenes_commands_service.create_client_order(
                    order_data=order_data_cliente,
                    authorization="Bearer test-token"
                )
            
            assert exc_info.value.status_code == 503

    @pytest.mark.asyncio
    async def test_create_order_unexpected_error(self, ordenes_commands_service, sample_order_data):
        """Test para error inesperado"""
        mock_client = AsyncMock()
        mock_client.__aenter__.return_value.post = AsyncMock(
            side_effect=Exception("Unexpected error")
        )
        
        with patch('httpx.AsyncClient', return_value=mock_client):
            with pytest.raises(HTTPException) as exc_info:
                await ordenes_commands_service.create_order(
                    order_data=sample_order_data,
                    authorization="Bearer test-token"
                )
            
            assert exc_info.value.status_code == 500
            assert "Error inesperado" in str(exc_info.value.detail)

