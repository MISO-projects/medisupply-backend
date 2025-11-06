import pytest
from unittest.mock import Mock, AsyncMock, patch, MagicMock
import httpx
from fastapi import HTTPException, UploadFile

from services.productos_service import ProductosService

pytestmark = pytest.mark.asyncio


class TestProductosService:
    
    @pytest.fixture
    def productos_service(self):
        with patch.dict('os.environ', {'PRODUCTOS_SERVICE_URL': 'http://test-productos-service:3000'}):
            return ProductosService()
    
    @pytest.fixture
    def mock_upload_file(self):
        """Fixture para crear un UploadFile mock"""
        upload_file = MagicMock(spec=UploadFile)
        upload_file.filename = "productos.xlsx"
        upload_file.content_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        upload_file.read = AsyncMock(return_value=b"fake excel content")
        upload_file.seek = AsyncMock()
        return upload_file

    def test_health_check_success(self, productos_service):
        """Test exitoso para health check"""
        mock_response = Mock()
        mock_response.json.return_value = {"status": "healthy"}
        mock_response.raise_for_status.return_value = None
        
        with patch('httpx.get', return_value=mock_response) as mock_get:
            result = productos_service.health_check()
            
            assert result == {"status": "healthy"}
            mock_get.assert_called_once_with("http://test-productos-service:3000/health", timeout=30.0)

    def test_health_check_service_error(self, productos_service):
        """Test para error del servicio en health check"""
        with patch('httpx.get') as mock_get:
            mock_response = Mock()
            mock_response.status_code = 500
            mock_get.side_effect = httpx.HTTPStatusError("Service error", request=Mock(), response=mock_response)
            
            with pytest.raises(HTTPException) as exc_info:
                productos_service.health_check()
            
            assert exc_info.value.status_code == 503

    def test_health_check_connection_error(self, productos_service):
        """Test para error de conexión en health check"""
        with patch('httpx.get') as mock_get:
            mock_get.side_effect = httpx.RequestError("Connection failed", request=Mock())
            
            with pytest.raises(HTTPException) as exc_info:
                productos_service.health_check()
            
            assert exc_info.value.status_code == 503

    def test_get_productos_creados_success(self, productos_service):
        """Test exitoso para obtener productos creados"""
        mock_response = Mock()
        mock_response.json.return_value = {
            "total": 10,
            "page": 1,
            "page_size": 20,
            "total_pages": 1,
            "productos": []
        }
        mock_response.raise_for_status.return_value = None
        
        with patch('httpx.get', return_value=mock_response) as mock_get:
            result = productos_service.get_productos_creados(page=1, page_size=20)
            
            assert result["total"] == 10
            mock_get.assert_called_once()
            call_args = mock_get.call_args
            assert "/api/productos/creados" in call_args[0][0]

    def test_get_producto_by_id_success(self, productos_service):
        """Test exitoso para obtener producto por ID"""
        producto_id = "test-id-123"
        mock_response = Mock()
        mock_response.json.return_value = {
            "id": producto_id,
            "nombre": "Paracetamol",
            "categoria": "MEDICAMENTOS"
        }
        mock_response.raise_for_status.return_value = None
        
        with patch('httpx.get', return_value=mock_response) as mock_get:
            result = productos_service.get_producto_by_id(producto_id)
            
            assert result["id"] == producto_id
            mock_get.assert_called_once_with(
                f"http://test-productos-service:3000/api/productos/{producto_id}",
                timeout=30.0
            )

    def test_get_producto_by_id_not_found(self, productos_service):
        """Test para producto no encontrado"""
        producto_id = "non-existent-id"
        
        with patch('httpx.get') as mock_get:
            mock_response = Mock()
            mock_response.status_code = 404
            mock_response.json.return_value = {"detail": "Producto no encontrado"}
            mock_get.side_effect = httpx.HTTPStatusError(
                "Not found",
                request=Mock(),
                response=mock_response
            )
            
            with pytest.raises(HTTPException) as exc_info:
                productos_service.get_producto_by_id(producto_id)
            
            assert exc_info.value.status_code == 404


class TestBulkUploadProductos:
    """Tests para bulk upload de productos"""

    @pytest.fixture
    def productos_service(self):
        with patch.dict('os.environ', {'PRODUCTOS_SERVICE_URL': 'http://test-productos-service:3000'}):
            return ProductosService()
    
    @pytest.fixture
    def mock_upload_file(self):
        """Fixture para crear un UploadFile mock"""
        upload_file = MagicMock(spec=UploadFile)
        upload_file.filename = "productos.xlsx"
        upload_file.content_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        upload_file.read = AsyncMock(return_value=b"fake excel content")
        upload_file.seek = AsyncMock(return_value=None)
        return upload_file

    async def test_bulk_upload_success(self, productos_service, mock_upload_file):
        """Test exitoso de bulk upload"""
        mock_response_data = {
            "total_rows": 5,
            "successful": 5,
            "failed": 0,
            "created": 5,
            "updated": 0,
            "skipped_duplicates": 0,
            "duplicate_rows": [],
            "errors": [],
            "created_products": ["id1", "id2", "id3", "id4", "id5"],
            "updated_products": []
        }
        
        mock_response = Mock()
        mock_response.json.return_value = mock_response_data
        mock_response.raise_for_status = Mock()
        
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_response)
        
        with patch('services.productos_service.httpx.AsyncClient') as mock_async_client_class:
            mock_async_client_instance = MagicMock()
            mock_async_client_instance.__aenter__ = AsyncMock(return_value=mock_client)
            mock_async_client_instance.__aexit__ = AsyncMock(return_value=None)
            mock_async_client_class.return_value = mock_async_client_instance
            
            result = await productos_service.bulk_upload_productos(mock_upload_file)
            
            assert result["total_rows"] == 5
            assert result["successful"] == 5
            assert result["created"] == 5
            assert result["updated"] == 0
            assert len(result["created_products"]) == 5
            
            mock_client.post.assert_called_once()
            call_args = mock_client.post.call_args
            assert "/api/productos/bulk-upload" in call_args[0][0]
            assert "files" in call_args[1]

    async def test_bulk_upload_with_errors(self, productos_service, mock_upload_file):
        """Test bulk upload con algunos errores"""
        mock_response_data = {
            "total_rows": 5,
            "successful": 3,
            "failed": 2,
            "created": 3,
            "updated": 0,
            "skipped_duplicates": 0,
            "duplicate_rows": [],
            "errors": [
                {"row": 2, "error": "Proveedor no encontrado", "data": None},
                {"row": 4, "error": "Precio inválido", "data": None}
            ],
            "created_products": ["id1", "id2", "id3"],
            "updated_products": []
        }
        
        mock_response = Mock()
        mock_response.json.return_value = mock_response_data
        mock_response.raise_for_status = Mock()
        
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_response)
        
        with patch('services.productos_service.httpx.AsyncClient') as mock_async_client_class:
            mock_async_client_instance = MagicMock()
            mock_async_client_instance.__aenter__ = AsyncMock(return_value=mock_client)
            mock_async_client_instance.__aexit__ = AsyncMock(return_value=None)
            mock_async_client_class.return_value = mock_async_client_instance
            result = await productos_service.bulk_upload_productos(mock_upload_file)
            
            assert result["successful"] == 3
            assert result["failed"] == 2
            assert len(result["errors"]) == 2

    async def test_bulk_upload_with_updates(self, productos_service, mock_upload_file):
        """Test bulk upload con productos actualizados"""
        mock_response_data = {
            "total_rows": 3,
            "successful": 3,
            "failed": 0,
            "created": 1,
            "updated": 2,
            "skipped_duplicates": 0,
            "duplicate_rows": [],
            "errors": [],
            "created_products": ["id-new"],
            "updated_products": ["id-existing-1", "id-existing-2"]
        }
        
        mock_response = Mock()
        mock_response.json.return_value = mock_response_data
        mock_response.raise_for_status = Mock()
        
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_response)
        
        with patch('services.productos_service.httpx.AsyncClient') as mock_async_client_class:
            mock_async_client_instance = MagicMock()
            mock_async_client_instance.__aenter__ = AsyncMock(return_value=mock_client)
            mock_async_client_instance.__aexit__ = AsyncMock(return_value=None)
            mock_async_client_class.return_value = mock_async_client_instance
            result = await productos_service.bulk_upload_productos(mock_upload_file)
            
            assert result["created"] == 1
            assert result["updated"] == 2
            assert len(result["created_products"]) == 1
            assert len(result["updated_products"]) == 2

    async def test_bulk_upload_service_400_error(self, productos_service, mock_upload_file):
        """Test cuando el servicio retorna error 400"""
        mock_response = Mock()
        mock_response.status_code = 400
        mock_response.json.return_value = {"detail": "Columnas requeridas faltantes: nombre"}
        
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(side_effect=httpx.HTTPStatusError(
            "Bad request",
            request=Mock(),
            response=mock_response
        ))
        
        with patch('services.productos_service.httpx.AsyncClient') as mock_async_client_class:
            mock_async_client_instance = MagicMock()
            mock_async_client_instance.__aenter__ = AsyncMock(return_value=mock_client)
            mock_async_client_instance.__aexit__ = AsyncMock(return_value=None)
            mock_async_client_class.return_value = mock_async_client_instance
            with pytest.raises(HTTPException) as exc_info:
                await productos_service.bulk_upload_productos(mock_upload_file)
            
            assert exc_info.value.status_code == 400
            assert "Columnas requeridas faltantes" in exc_info.value.detail

    async def test_bulk_upload_service_500_error(self, productos_service, mock_upload_file):
        """Test cuando el servicio retorna error 500"""
        mock_response = Mock()
        mock_response.status_code = 500
        mock_response.json.return_value = {"detail": "Error interno del servidor"}
        
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client.post = AsyncMock(side_effect=httpx.HTTPStatusError(
            "Internal server error",
            request=Mock(),
            response=mock_response
        ))
        
        with patch('httpx.AsyncClient', return_value=mock_client):
            with pytest.raises(HTTPException) as exc_info:
                await productos_service.bulk_upload_productos(mock_upload_file)
            
            assert exc_info.value.status_code == 500
            assert "Error del servicio de productos" in exc_info.value.detail

    async def test_bulk_upload_connection_error(self, productos_service, mock_upload_file):
        """Test cuando no se puede conectar al servicio"""
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(side_effect=httpx.RequestError("Connection failed", request=Mock()))
        
        with patch('services.productos_service.httpx.AsyncClient') as mock_async_client_class:
            mock_async_client_instance = MagicMock()
            mock_async_client_instance.__aenter__ = AsyncMock(return_value=mock_client)
            mock_async_client_instance.__aexit__ = AsyncMock(return_value=None)
            mock_async_client_class.return_value = mock_async_client_instance
            with pytest.raises(HTTPException) as exc_info:
                await productos_service.bulk_upload_productos(mock_upload_file)
            
            assert exc_info.value.status_code == 503
            assert "No se puede conectar con el servicio de productos" in exc_info.value.detail

    async def test_bulk_upload_file_read(self, productos_service, mock_upload_file):
        """Test que el archivo se lee correctamente"""
        mock_response_data = {
            "total_rows": 1,
            "successful": 1,
            "failed": 0,
            "created": 1,
            "updated": 0,
            "skipped_duplicates": 0,
            "duplicate_rows": [],
            "errors": [],
            "created_products": ["id1"],
            "updated_products": []
        }
        
        mock_response = Mock()
        mock_response.json.return_value = mock_response_data
        mock_response.raise_for_status = Mock()
        
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_response)
        
        with patch('services.productos_service.httpx.AsyncClient') as mock_async_client_class:
            mock_async_client_instance = MagicMock()
            mock_async_client_instance.__aenter__ = AsyncMock(return_value=mock_client)
            mock_async_client_instance.__aexit__ = AsyncMock(return_value=None)
            mock_async_client_class.return_value = mock_async_client_instance
            await productos_service.bulk_upload_productos(mock_upload_file)
            
            mock_upload_file.read.assert_called_once()
            mock_upload_file.seek.assert_called_once_with(0)

    async def test_bulk_upload_timeout(self, productos_service, mock_upload_file):
        """Test que usa el timeout correcto (120 segundos)"""
        mock_response_data = {
            "total_rows": 1,
            "successful": 1,
            "failed": 0,
            "created": 1,
            "updated": 0,
            "skipped_duplicates": 0,
            "duplicate_rows": [],
            "errors": [],
            "created_products": ["id1"],
            "updated_products": []
        }
        
        mock_response = Mock()
        mock_response.json.return_value = mock_response_data
        mock_response.raise_for_status = Mock()
        
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_response)
        
        with patch('services.productos_service.httpx.AsyncClient') as mock_async_client_class:
            mock_async_client_instance = MagicMock()
            mock_async_client_instance.__aenter__ = AsyncMock(return_value=mock_client)
            mock_async_client_instance.__aexit__ = AsyncMock(return_value=None)
            mock_async_client_class.return_value = mock_async_client_instance
            
            await productos_service.bulk_upload_productos(mock_upload_file)
            
            mock_async_client_class.assert_called_once_with(timeout=120.0)

