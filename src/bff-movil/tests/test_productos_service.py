import pytest
from unittest.mock import Mock, patch, AsyncMock
import httpx
from fastapi import HTTPException

from services.productos_service import ProductosService


class TestProductosService:
    
    @pytest.fixture
    def productos_service(self):
        with patch.dict('os.environ', {'PRODUCTOS_SERVICE_URL': 'http://test-service:3000'}):
            return ProductosService()
    
    @pytest.fixture
    def sample_productos_response(self):
        return {
            "total": 2,
            "page": 1,
            "page_size": 20,
            "total_pages": 1,
            "productos": [
                {
                    "id": "P001",
                    "nombre": "Paracetamol 500mg",
                    "categoria": "MEDICAMENTOS",
                    "stock_disponible": 100
                },
                {
                    "id": "P002",
                    "nombre": "Guantes Médicos",
                    "categoria": "INSUMOS",
                    "stock_disponible": 50
                }
            ]
        }
    
    @pytest.fixture
    def sample_producto_response(self):
        return {
            "id": "P001",
            "nombre": "Paracetamol 500mg",
            "categoria": "MEDICAMENTOS",
            "stock_disponible": 100,
            "precio_unitario": 15.50
        }

    def test_health_check_success(self, productos_service):
        """Test exitoso para health check"""
        mock_response = Mock()
        mock_response.json.return_value = {"status": "healthy"}
        mock_response.raise_for_status.return_value = None
        
        with patch('httpx.get', return_value=mock_response) as mock_get:
            result = productos_service.health_check()
            
            assert result == {"status": "healthy"}
            mock_get.assert_called_once_with("http://test-service:3000/health", timeout=30.0)

    def test_health_check_service_error(self, productos_service):
        """Test para error del servicio"""
        with patch('httpx.get') as mock_get:
            mock_get.side_effect = httpx.HTTPStatusError("Service error", request=Mock(), response=Mock())
            
            with pytest.raises(HTTPException) as exc_info:
                productos_service.health_check()
            
            assert exc_info.value.status_code == 503

    def test_health_check_connection_error(self, productos_service):
        """Test para error de conexión"""
        with patch('httpx.get') as mock_get:
            mock_get.side_effect = httpx.RequestError("Connection error")
            
            with pytest.raises(HTTPException) as exc_info:
                productos_service.health_check()
            
            assert exc_info.value.status_code == 503

    def test_get_productos_disponibles_success(self, productos_service, sample_productos_response):
        """Test exitoso para obtener productos disponibles"""
        mock_response = Mock()
        mock_response.json.return_value = sample_productos_response
        mock_response.raise_for_status.return_value = None
        
        with patch('httpx.get', return_value=mock_response) as mock_get:
            result = productos_service.get_productos_disponibles(
                solo_con_stock=True,
                categoria="MEDICAMENTOS",
                nombre="Paracetamol",
                page=1,
                page_size=20
            )
            
            assert result == sample_productos_response
            mock_get.assert_called_once()
            call_args = mock_get.call_args
            assert "/api/productos/disponibles" in call_args[0][0]
            assert call_args[1]["params"]["solo_con_stock"] is True
            assert call_args[1]["params"]["categoria"] == "MEDICAMENTOS"
            assert call_args[1]["params"]["nombre"] == "Paracetamol"

    def test_get_productos_disponibles_not_found(self, productos_service):
        """Test para productos no encontrados"""
        mock_response = Mock()
        mock_response.status_code = 404
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "Not Found", request=Mock(), response=mock_response
        )
        
        with patch('httpx.get', return_value=mock_response):
            with pytest.raises(HTTPException) as exc_info:
                productos_service.get_productos_disponibles()
            
            assert exc_info.value.status_code == 404
            assert "No se encontraron productos disponibles" in str(exc_info.value.detail)

    def test_get_productos_disponibles_service_unavailable(self, productos_service):
        """Test para servicio no disponible"""
        with patch('httpx.get') as mock_get:
            mock_get.side_effect = httpx.RequestError("Service unavailable")
            
            with pytest.raises(HTTPException) as exc_info:
                productos_service.get_productos_disponibles()
            
            assert exc_info.value.status_code == 503

    def test_get_producto_by_id_success(self, productos_service, sample_producto_response):
        """Test exitoso para obtener producto por ID"""
        mock_response = Mock()
        mock_response.json.return_value = sample_producto_response
        mock_response.raise_for_status.return_value = None
        
        with patch('httpx.get', return_value=mock_response) as mock_get:
            result = productos_service.get_producto_by_id("P001")
            
            assert result == sample_producto_response
            mock_get.assert_called_once_with(
                "http://test-service:3000/api/productos/P001",
                timeout=30.0
            )

    def test_get_producto_by_id_not_found(self, productos_service):
        """Test para producto no encontrado"""
        mock_response = Mock()
        mock_response.status_code = 404
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "Not Found", request=Mock(), response=mock_response
        )
        
        with patch('httpx.get', return_value=mock_response):
            with pytest.raises(HTTPException) as exc_info:
                productos_service.get_producto_by_id("P999")
            
            assert exc_info.value.status_code == 404
            assert "Producto P999 no encontrado" in str(exc_info.value.detail)

    def test_get_producto_by_id_service_unavailable(self, productos_service):
        """Test para servicio no disponible"""
        with patch('httpx.get') as mock_get:
            mock_get.side_effect = httpx.RequestError("Service unavailable")
            
            with pytest.raises(HTTPException) as exc_info:
                productos_service.get_producto_by_id("P001")
            
            assert exc_info.value.status_code == 503

    @pytest.mark.asyncio
    async def test_get_productos_by_ids_success(self, productos_service):
        """Test exitoso para obtener productos por IDs"""
        sample_response = [
            {"id": "P001", "nombre": "Producto 1"},
            {"id": "P002", "nombre": "Producto 2"}
        ]
        
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = sample_response
        
        mock_client = AsyncMock()
        mock_client.__aenter__.return_value.post = AsyncMock(return_value=mock_response)
        mock_client.__aexit__.return_value = None
        
        with patch('httpx.AsyncClient', return_value=mock_client):
            result = await productos_service.get_productos_by_ids(["P001", "P002"])
            
            assert result == sample_response
            mock_client.__aenter__.return_value.post.assert_called_once()
            call_args = mock_client.__aenter__.return_value.post.call_args
            assert "/api/productos/by-ids" in call_args[0][0]
            assert call_args[1]["json"] == {"ids": ["P001", "P002"]}

    @pytest.mark.asyncio
    async def test_get_productos_by_ids_empty_list(self, productos_service):
        """Test para lista vacía de IDs"""
        result = await productos_service.get_productos_by_ids([])
        
        assert result == []

    @pytest.mark.asyncio
    async def test_get_productos_by_ids_service_error(self, productos_service):
        """Test para error del servicio"""
        mock_response = Mock()
        mock_response.status_code = 500
        mock_response.text = "Internal Server Error"
        
        mock_client = AsyncMock()
        mock_client.__aenter__.return_value.post = AsyncMock(return_value=mock_response)
        
        with patch('httpx.AsyncClient', return_value=mock_client):
            with pytest.raises(HTTPException) as exc_info:
                await productos_service.get_productos_by_ids(["P001"])
            
            assert exc_info.value.status_code == 500

    @pytest.mark.asyncio
    async def test_get_productos_by_ids_service_unavailable(self, productos_service):
        """Test para servicio no disponible"""
        mock_client = AsyncMock()
        mock_client.__aenter__.return_value.post = AsyncMock(
            side_effect=httpx.RequestError("Service unavailable")
        )
        
        with patch('httpx.AsyncClient', return_value=mock_client):
            with pytest.raises(HTTPException) as exc_info:
                await productos_service.get_productos_by_ids(["P001"])
            
            assert exc_info.value.status_code == 503
            assert "Servicio de productos no disponible" in str(exc_info.value.detail)

