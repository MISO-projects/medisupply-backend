import pytest
from unittest.mock import Mock, AsyncMock, patch
import httpx
from fastapi import HTTPException
from datetime import datetime

from services.ordenes_queries_service import OrdenesQueriesService


class TestOrdenesQueriesService:
    
    @pytest.fixture
    def ordenes_queries_service(self):
        with patch.dict('os.environ', {'ORDENES_QUERIES_SERVICE_URL': 'http://test-service:3000'}):
            return OrdenesQueriesService()
    
    @pytest.fixture
    def sample_orders_response(self):
        return {
            "data": [
                {
                    "id": "ORD-001",
                    "numero_orden": "ORD-251025-A1B2C3D4",
                    "estado": "PENDIENTE",
                    "valor_total": 150.00
                }
            ],
            "total": 1,
            "page": 1,
            "page_size": 20,
            "total_pages": 1
        }
    
    @pytest.fixture
    def sample_order_response(self):
        return {
            "data": {
                "id": "ORD-001",
                "numero_orden": "ORD-251025-A1B2C3D4",
                "estado": "PENDIENTE",
                "valor_total": 150.00,
                "detalles": []
            }
        }

    def test_health_check_success(self, ordenes_queries_service):
        """Test exitoso para health check"""
        mock_response = Mock()
        mock_response.json.return_value = {"status": "healthy"}
        mock_response.raise_for_status.return_value = None
        
        with patch('httpx.get', return_value=mock_response) as mock_get:
            result = ordenes_queries_service.health_check()
            
            assert result == {"status": "healthy"}
            mock_get.assert_called_once_with("http://test-service:3000/health", timeout=30.0)

    def test_health_check_service_error(self, ordenes_queries_service):
        """Test para error del servicio"""
        with patch('httpx.get') as mock_get:
            mock_get.side_effect = httpx.HTTPStatusError("Service error", request=Mock(), response=Mock())
            
            with pytest.raises(HTTPException) as exc_info:
                ordenes_queries_service.health_check()
            
            assert exc_info.value.status_code == 503

    def test_health_check_connection_error(self, ordenes_queries_service):
        """Test para error de conexión"""
        with patch('httpx.get') as mock_get:
            mock_get.side_effect = httpx.RequestError("Connection error")
            
            with pytest.raises(HTTPException) as exc_info:
                ordenes_queries_service.health_check()
            
            assert exc_info.value.status_code == 503

    @pytest.mark.asyncio
    async def test_listar_ordenes_success(self, ordenes_queries_service, sample_orders_response):
        """Test exitoso para listar órdenes"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = sample_orders_response
        
        mock_client = AsyncMock()
        mock_client.__aenter__.return_value.get = AsyncMock(return_value=mock_response)
        mock_client.__aexit__.return_value = None
        
        with patch('httpx.AsyncClient', return_value=mock_client):
            result = await ordenes_queries_service.listar_ordenes(
                estado="PENDIENTE",
                page=1,
                page_size=20
            )
            
            assert result == sample_orders_response
            mock_client.__aenter__.return_value.get.assert_called_once()
            call_args = mock_client.__aenter__.return_value.get.call_args
            assert "/orders/" in call_args[0][0]
            assert call_args[1]["params"]["estado"] == "PENDIENTE"

    @pytest.mark.asyncio
    async def test_listar_ordenes_with_dates(self, ordenes_queries_service, sample_orders_response):
        """Test para listar órdenes con fechas"""
        fecha_desde = datetime(2025, 1, 1)
        fecha_hasta = datetime(2025, 1, 31)
        
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = sample_orders_response
        
        mock_client = AsyncMock()
        mock_client.__aenter__.return_value.get = AsyncMock(return_value=mock_response)
        
        with patch('httpx.AsyncClient', return_value=mock_client):
            result = await ordenes_queries_service.listar_ordenes(
                fecha_creacion_desde=fecha_desde,
                fecha_creacion_hasta=fecha_hasta
            )
            
            assert result == sample_orders_response
            call_args = mock_client.__aenter__.return_value.get.call_args
            params = call_args[1]["params"]
            assert "fecha_creacion_desde" in params
            assert "fecha_creacion_hasta" in params

    @pytest.mark.asyncio
    async def test_listar_ordenes_service_error(self, ordenes_queries_service):
        """Test para error del servicio"""
        mock_response = Mock()
        mock_response.status_code = 500
        mock_response.text = "Internal Server Error"
        
        mock_client = AsyncMock()
        mock_client.__aenter__.return_value.get = AsyncMock(return_value=mock_response)
        
        with patch('httpx.AsyncClient', return_value=mock_client):
            with pytest.raises(HTTPException) as exc_info:
                await ordenes_queries_service.listar_ordenes()
            
            assert exc_info.value.status_code == 500

    @pytest.mark.asyncio
    async def test_listar_ordenes_service_unavailable(self, ordenes_queries_service):
        """Test para servicio no disponible"""
        mock_client = AsyncMock()
        mock_client.__aenter__.return_value.get = AsyncMock(
            side_effect=httpx.RequestError("Service unavailable")
        )
        
        with patch('httpx.AsyncClient', return_value=mock_client):
            with pytest.raises(HTTPException) as exc_info:
                await ordenes_queries_service.listar_ordenes()
            
            assert exc_info.value.status_code == 503
            assert "Ordenes queries service is not available" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_obtener_orden_success(self, ordenes_queries_service, sample_order_response):
        """Test exitoso para obtener orden por ID"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = sample_order_response
        
        mock_client = AsyncMock()
        mock_client.__aenter__.return_value.get = AsyncMock(return_value=mock_response)
        
        with patch('httpx.AsyncClient', return_value=mock_client):
            result = await ordenes_queries_service.obtener_orden("ORD-001")
            
            assert result == sample_order_response
            mock_client.__aenter__.return_value.get.assert_called_once_with(
                "http://test-service:3000/orders/ORD-001"
            )

    @pytest.mark.asyncio
    async def test_obtener_orden_not_found(self, ordenes_queries_service):
        """Test para orden no encontrada"""
        mock_response = Mock()
        mock_response.status_code = 404
        
        mock_client = AsyncMock()
        mock_client.__aenter__.return_value.get = AsyncMock(return_value=mock_response)
        
        with patch('httpx.AsyncClient', return_value=mock_client):
            with pytest.raises(HTTPException) as exc_info:
                await ordenes_queries_service.obtener_orden("ORD-999")
            
            assert exc_info.value.status_code == 404
            assert "Orden no encontrada" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_obtener_orden_service_unavailable(self, ordenes_queries_service):
        """Test para servicio no disponible"""
        mock_client = AsyncMock()
        mock_client.__aenter__.return_value.get = AsyncMock(
            side_effect=httpx.RequestError("Service unavailable")
        )
        
        with patch('httpx.AsyncClient', return_value=mock_client):
            with pytest.raises(HTTPException) as exc_info:
                await ordenes_queries_service.obtener_orden("ORD-001")
            
            assert exc_info.value.status_code == 503

    @pytest.mark.asyncio
    async def test_obtener_ordenes_cliente_success(self, ordenes_queries_service, sample_orders_response):
        """Test exitoso para obtener órdenes del cliente"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = sample_orders_response
        
        mock_client = AsyncMock()
        mock_client.__aenter__.return_value.get = AsyncMock(return_value=mock_response)
        
        with patch('httpx.AsyncClient', return_value=mock_client):
            result = await ordenes_queries_service.obtener_ordenes_cliente(
                authorization="Bearer test-token",
                page=1,
                page_size=20
            )
            
            assert result == sample_orders_response
            mock_client.__aenter__.return_value.get.assert_called_once()
            call_args = mock_client.__aenter__.return_value.get.call_args
            assert "/orders/client-orders" in call_args[0][0]
            assert call_args[1]["headers"]["Authorization"] == "Bearer test-token"
            assert call_args[1]["params"]["page"] == 1
            assert call_args[1]["params"]["page_size"] == 20

    @pytest.mark.asyncio
    async def test_obtener_ordenes_cliente_unauthorized(self, ordenes_queries_service):
        """Test para token no autorizado"""
        mock_response = Mock()
        mock_response.status_code = 401
        
        mock_client = AsyncMock()
        mock_client.__aenter__.return_value.get = AsyncMock(return_value=mock_response)
        
        with patch('httpx.AsyncClient', return_value=mock_client):
            with pytest.raises(HTTPException) as exc_info:
                await ordenes_queries_service.obtener_ordenes_cliente(
                    authorization="Bearer invalid-token"
                )
            
            assert exc_info.value.status_code == 401
            assert "No autorizado" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_obtener_ordenes_cliente_forbidden(self, ordenes_queries_service):
        """Test para acceso denegado"""
        mock_response = Mock()
        mock_response.status_code = 403
        
        mock_client = AsyncMock()
        mock_client.__aenter__.return_value.get = AsyncMock(return_value=mock_response)
        
        with patch('httpx.AsyncClient', return_value=mock_client):
            with pytest.raises(HTTPException) as exc_info:
                await ordenes_queries_service.obtener_ordenes_cliente(
                    authorization="Bearer test-token"
                )
            
            assert exc_info.value.status_code == 403
            assert "Acceso denegado" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_obtener_ordenes_cliente_service_unavailable(self, ordenes_queries_service):
        """Test para servicio no disponible"""
        mock_client = AsyncMock()
        mock_client.__aenter__.return_value.get = AsyncMock(
            side_effect=httpx.RequestError("Service unavailable")
        )
        
        with patch('httpx.AsyncClient', return_value=mock_client):
            with pytest.raises(HTTPException) as exc_info:
                await ordenes_queries_service.obtener_ordenes_cliente(
                    authorization="Bearer test-token"
                )
            
            assert exc_info.value.status_code == 503

