import pytest
from unittest.mock import AsyncMock, MagicMock, Mock
from fastapi.testclient import TestClient
from fastapi import HTTPException

from main import app
from router.productos import get_productos_service
from services.productos_service import ProductosService


@pytest.fixture
def client():
    """Cliente de prueba de FastAPI"""
    return TestClient(app)


@pytest.fixture(autouse=True)
def clear_overrides():
    """Limpia los overrides después de cada test"""
    yield
    app.dependency_overrides.clear()


class TestProductosRouterBulkUpload:
    """Tests del endpoint de bulk upload en el router"""

    def test_bulk_upload_success(self, client):
        """Test exitoso de bulk upload"""
        mock_service = MagicMock(spec=ProductosService)
        mock_service.bulk_upload_productos = AsyncMock(return_value={
            "total_rows": 3,
            "successful": 3,
            "failed": 0,
            "created": 3,
            "updated": 0,
            "skipped_duplicates": 0,
            "duplicate_rows": [],
            "errors": [],
            "created_products": ["id1", "id2", "id3"],
            "updated_products": []
        })
        
        app.dependency_overrides[get_productos_service] = lambda: mock_service
        
        files = {
            "file": ("productos.xlsx", b"fake excel content", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        }
        
        response = client.post("/productos/bulk-upload", files=files)
        
        assert response.status_code == 201
        result = response.json()
        assert result["total_rows"] == 3
        assert result["successful"] == 3
        assert result["created"] == 3

    def test_bulk_upload_invalid_file_extension(self, client):
        """Test con extensión de archivo inválida"""
        mock_service = MagicMock(spec=ProductosService)
        app.dependency_overrides[get_productos_service] = lambda: mock_service
        
        files = {
            "file": ("productos.txt", b"not an excel file", "text/plain")
        }
        
        response = client.post("/productos/bulk-upload", files=files)
        
        assert response.status_code == 400
        assert "Excel" in response.json()["detail"]
        mock_service.bulk_upload_productos.assert_not_called()

    def test_bulk_upload_xls_extension(self, client):
        """Test que acepta archivos .xls además de .xlsx"""
        mock_service = MagicMock(spec=ProductosService)
        mock_service.bulk_upload_productos = AsyncMock(return_value={
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
        })
        
        app.dependency_overrides[get_productos_service] = lambda: mock_service
        
        files = {
            "file": ("productos.xls", b"fake excel content", "application/vnd.ms-excel")
        }
        
        response = client.post("/productos/bulk-upload", files=files)
        
        assert response.status_code == 201

    def test_bulk_upload_service_error(self, client):
        """Test cuando el servicio retorna error"""
        mock_service = MagicMock(spec=ProductosService)
        mock_service.bulk_upload_productos = AsyncMock(side_effect=HTTPException(
            status_code=400,
            detail="Columnas requeridas faltantes"
        ))
        
        app.dependency_overrides[get_productos_service] = lambda: mock_service
        
        files = {
            "file": ("productos.xlsx", b"fake excel content", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        }
        
        response = client.post("/productos/bulk-upload", files=files)
        
        assert response.status_code == 400
        assert "Columnas requeridas faltantes" in response.json()["detail"]

    def test_bulk_upload_with_errors(self, client):
        """Test bulk upload con algunos errores"""
        mock_service = MagicMock(spec=ProductosService)
        mock_service.bulk_upload_productos = AsyncMock(return_value={
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
        })
        
        app.dependency_overrides[get_productos_service] = lambda: mock_service
        
        files = {
            "file": ("productos.xlsx", b"fake excel content", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        }
        
        response = client.post("/productos/bulk-upload", files=files)
        
        assert response.status_code == 201
        result = response.json()
        assert result["successful"] == 3
        assert result["failed"] == 2
        assert len(result["errors"]) == 2

    def test_bulk_upload_with_duplicates(self, client):
        """Test bulk upload con duplicados"""
        mock_service = MagicMock(spec=ProductosService)
        mock_service.bulk_upload_productos = AsyncMock(return_value={
            "total_rows": 5,
            "successful": 3,
            "failed": 0,
            "created": 3,
            "updated": 0,
            "skipped_duplicates": 2,
            "duplicate_rows": [3, 5],
            "errors": [],
            "created_products": ["id1", "id2", "id3"],
            "updated_products": []
        })
        
        app.dependency_overrides[get_productos_service] = lambda: mock_service
        
        files = {
            "file": ("productos.xlsx", b"fake excel content", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        }
        
        response = client.post("/productos/bulk-upload", files=files)
        
        assert response.status_code == 201
        result = response.json()
        assert result["skipped_duplicates"] == 2
        assert len(result["duplicate_rows"]) == 2

    def test_bulk_upload_internal_error(self, client):
        """Test cuando hay un error interno"""
        mock_service = MagicMock(spec=ProductosService)
        mock_service.bulk_upload_productos = AsyncMock(side_effect=Exception("Internal error"))
        
        app.dependency_overrides[get_productos_service] = lambda: mock_service
        
        files = {
            "file": ("productos.xlsx", b"fake excel content", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        }
        
        response = client.post("/productos/bulk-upload", files=files)
        
        assert response.status_code == 500
        assert "Error interno del servidor BFF web" in response.json()["detail"]

    def test_bulk_upload_with_updates(self, client):
        """Test bulk upload con productos actualizados"""
        mock_service = MagicMock(spec=ProductosService)
        mock_service.bulk_upload_productos = AsyncMock(return_value={
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
        })
        
        app.dependency_overrides[get_productos_service] = lambda: mock_service
        
        files = {
            "file": ("productos.xlsx", b"fake excel content", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        }
        
        response = client.post("/productos/bulk-upload", files=files)
        
        assert response.status_code == 201
        result = response.json()
        assert result["created"] == 1
        assert result["updated"] == 2
        assert len(result["updated_products"]) == 2

    def test_bulk_upload_missing_file(self, client):
        """Test sin enviar archivo"""
        response = client.post("/productos/bulk-upload")
        
        assert response.status_code == 422  # Validation error


class TestProductosRouterOtherEndpoints:
    """Tests de otros endpoints del router de productos"""

    def test_get_productos_creados(self, client):
        """Test obtener productos creados"""
        mock_service = MagicMock(spec=ProductosService)
        mock_service.get_productos_creados = Mock(return_value={
            "total": 10,
            "page": 1,
            "page_size": 20,
            "total_pages": 1,
            "productos": []
        })
        
        app.dependency_overrides[get_productos_service] = lambda: mock_service
        
        response = client.get("/productos/disponibles?page=1&page_size=20")
        
        assert response.status_code == 200
        result = response.json()
        assert result["total"] == 10

    def test_get_producto_by_id(self, client):
        """Test obtener producto por ID"""
        producto_id = "test-id-123"
        mock_service = MagicMock(spec=ProductosService)
        mock_service.get_producto_by_id = Mock(return_value={
            "id": producto_id,
            "nombre": "Paracetamol",
            "categoria": "MEDICAMENTOS"
        })
        
        app.dependency_overrides[get_productos_service] = lambda: mock_service
        
        response = client.get(f"/productos/{producto_id}")
        
        assert response.status_code == 200
        result = response.json()
        assert result["id"] == producto_id
