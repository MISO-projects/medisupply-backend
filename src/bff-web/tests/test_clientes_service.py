import pytest
from unittest.mock import Mock, patch
import httpx
from fastapi import HTTPException

from services.clientes_service import ClientesService


class TestClientesService:
    
    @pytest.fixture
    def clientes_service(self):
        with patch.dict('os.environ', {'CLIENTES_SERVICE_URL': 'http://test-service:3000'}):
            return ClientesService()
    
    @pytest.fixture
    def sample_response(self):
        return {
            "clientes": [
                {
                    "id": "C001",
                    "nombre": "Hospital General",
                    "nit": "901234567-8",
                    "logoUrl": "https://storage.googleapis.com/logos/hospital-general.png"
                }
            ],
            "total": 1
        }

    def test_health_check_success(self, clientes_service):
        """Test exitoso para health check"""
        mock_response = Mock()
        mock_response.json.return_value = {"status": "healthy"}
        mock_response.raise_for_status.return_value = None
        
        with patch('httpx.get', return_value=mock_response) as mock_get:
            result = clientes_service.health_check()
            
            assert result == {"status": "healthy"}
            mock_get.assert_called_once_with("http://test-service:3000/health", timeout=30.0)

    def test_health_check_service_error(self, clientes_service):
        """Test para error del servicio"""
        with patch('httpx.get') as mock_get:
            mock_get.side_effect = httpx.HTTPStatusError("Service error", request=Mock(), response=Mock())
            
            with pytest.raises(HTTPException) as exc_info:
                clientes_service.health_check()
            
            assert exc_info.value.status_code == 503

    def test_health_check_connection_error(self, clientes_service):
        """Test para error de conexión"""
        with patch('httpx.get') as mock_get:
            mock_get.side_effect = httpx.RequestError("Connection error")
            
            with pytest.raises(HTTPException) as exc_info:
                clientes_service.health_check()
            
            assert exc_info.value.status_code == 503

    def test_get_clientes_asignados_success(self, clientes_service, sample_response):
        """Test exitoso para obtener clientes asignados"""
        mock_response = Mock()
        mock_response.json.return_value = sample_response
        mock_response.raise_for_status.return_value = None
        
        with patch('httpx.get', return_value=mock_response) as mock_get:
            result = clientes_service.get_clientes_asignados("Bearer test-token")
            
            assert result == sample_response
            mock_get.assert_called_once_with(
                "http://test-service:3000/api/clientes/asignados",
                headers={
                    "Authorization": "Bearer test-token",
                    "Content-Type": "application/json"
                },
                timeout=30.0
            )

    def test_get_clientes_asignados_unauthorized(self, clientes_service):
        """Test para token no autorizado"""
        mock_response = Mock()
        mock_response.status_code = 401
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "Unauthorized", request=Mock(), response=mock_response
        )
        
        with patch('httpx.get', return_value=mock_response):
            with pytest.raises(HTTPException) as exc_info:
                clientes_service.get_clientes_asignados("Bearer invalid-token")
            
            assert exc_info.value.status_code == 401
            assert "Token de autorización inválido" in str(exc_info.value.detail)

    def test_get_clientes_asignados_not_found(self, clientes_service):
        """Test para no encontrado"""
        mock_response = Mock()
        mock_response.status_code = 404
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "Not Found", request=Mock(), response=mock_response
        )
        
        with patch('httpx.get', return_value=mock_response):
            with pytest.raises(HTTPException) as exc_info:
                clientes_service.get_clientes_asignados("Bearer test-token")
            
            assert exc_info.value.status_code == 404
            assert "No se encontraron clientes asignados" in str(exc_info.value.detail)

    def test_get_clientes_asignados_service_unavailable(self, clientes_service):
        """Test para servicio no disponible"""
        with patch('httpx.get') as mock_get:
            mock_get.side_effect = httpx.RequestError("Service unavailable")
            
            with pytest.raises(HTTPException) as exc_info:
                clientes_service.get_clientes_asignados("Bearer test-token")
            
            assert exc_info.value.status_code == 503
            assert "No se puede conectar" in str(exc_info.value.detail)

    def test_get_cliente_asignado_success(self, clientes_service):
        """Test exitoso para obtener cliente específico"""
        cliente_data = {
            "id": "C001",
            "nombre": "Hospital General",
            "nit": "901234567-8",
            "logoUrl": "https://storage.googleapis.com/logos/hospital-general.png"
        }
        
        mock_response = Mock()
        mock_response.json.return_value = cliente_data
        mock_response.raise_for_status.return_value = None
        
        with patch('httpx.get', return_value=mock_response) as mock_get:
            result = clientes_service.get_cliente_asignado("C001", "Bearer test-token")
            
            assert result == cliente_data
            mock_get.assert_called_once_with(
                "http://test-service:3000/api/clientes/asignados/C001",
                headers={
                    "Authorization": "Bearer test-token",
                    "Content-Type": "application/json"
                },
                timeout=30.0
            )

    def test_get_cliente_asignado_not_found(self, clientes_service):
        """Test para cliente no encontrado"""
        mock_response = Mock()
        mock_response.status_code = 404
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "Not Found", request=Mock(), response=mock_response
        )
        
        with patch('httpx.get', return_value=mock_response):
            with pytest.raises(HTTPException) as exc_info:
                clientes_service.get_cliente_asignado("C999", "Bearer test-token")
            
            assert exc_info.value.status_code == 404
            assert "Cliente C999 no encontrado" in str(exc_info.value.detail)

    def test_get_cliente_asignado_unauthorized(self, clientes_service):
        """Test para cliente no autorizado"""
        mock_response = Mock()
        mock_response.status_code = 401
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "Unauthorized", request=Mock(), response=mock_response
        )
        
        with patch('httpx.get', return_value=mock_response):
            with pytest.raises(HTTPException) as exc_info:
                clientes_service.get_cliente_asignado("C001", "Bearer invalid-token")
            
            assert exc_info.value.status_code == 401
            assert "Token de autorización inválido" in str(exc_info.value.detail)

    def test_unexpected_error(self, clientes_service):
        """Test para error inesperado"""
        with patch('httpx.get') as mock_get:
            mock_get.side_effect = Exception("Unexpected error")
            
            with pytest.raises(HTTPException) as exc_info:
                clientes_service.get_clientes_asignados("Bearer test-token")
            
            assert exc_info.value.status_code == 500
            assert "Error interno del servidor" in str(exc_info.value.detail)
