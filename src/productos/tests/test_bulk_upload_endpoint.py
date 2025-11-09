import pytest
import io
import pandas as pd
from uuid import uuid4
from unittest.mock import patch, AsyncMock


def create_excel_file(data):
    """Helper para crear un archivo Excel en memoria"""
    df = pd.DataFrame(data)
    output = io.BytesIO()
    df.to_excel(output, index=False, engine='openpyxl')
    output.seek(0)
    return output


class TestBulkUploadEndpoint:
    """Tests del endpoint de bulk upload"""

    @patch('services.productos_service.ProductosService._verificar_proveedor_activo')
    def test_bulk_upload_success(self, mock_verificar, client):
        """Test exitoso de bulk upload"""
        proveedor_id = str(uuid4())
        mock_verificar.return_value = {"id": proveedor_id, "nombre": "Proveedor Test"}
        
        data = [
            {
                "nombre": "Paracetamol 500mg",
                "categoria": "MEDICAMENTOS",
                "precio_unitario": 15.50,
                "proveedor_id": proveedor_id,
                "sku": "MED-001"
            },
            {
                "nombre": "Ibuprofeno 400mg",
                "categoria": "MEDICAMENTOS",
                "precio_unitario": 20.00,
                "proveedor_id": proveedor_id,
                "sku": "MED-002"
            }
        ]
        
        excel_data = create_excel_file(data)
        
        response = client.post(
            "/api/productos/bulk-upload",
            files={"file": ("productos.xlsx", excel_data, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")}
        )
        
        assert response.status_code == 201
        result = response.json()
        
        assert result["total_rows"] == 2
        assert result["successful"] == 2
        assert result["created"] == 2
        assert result["updated"] == 0
        assert result["failed"] == 0
        assert len(result["created_products"]) == 2

    def test_bulk_upload_archivo_invalido(self, client):
        """Test con archivo no Excel"""
        response = client.post(
            "/api/productos/bulk-upload",
            files={"file": ("test.txt", b"not an excel file", "text/plain")}
        )
        
        assert response.status_code == 400
        assert "Excel" in response.json()["detail"]

    def test_bulk_upload_sin_archivo(self, client):
        """Test sin enviar archivo"""
        response = client.post("/api/productos/bulk-upload")
        
        assert response.status_code == 422  # Validation error

    @patch('services.productos_service.ProductosService._verificar_proveedor_activo')
    def test_bulk_upload_con_errores(self, mock_verificar, client):
        """Test con algunos productos con errores"""
        proveedor_id = str(uuid4())
        mock_verificar.return_value = {"id": proveedor_id, "nombre": "Proveedor Test"}
        
        data = [
            {
                "nombre": "Producto Válido",
                "categoria": "MEDICAMENTOS",
                "precio_unitario": 15.50,
                "proveedor_id": proveedor_id,
                "sku": "MED-001"
            },
            {
                "nombre": "Producto Inválido",
                "categoria": "MEDICAMENTOS",
                "precio_unitario": -10.00,  # Precio negativo
                "proveedor_id": proveedor_id,
                "sku": "MED-002"
            }
        ]
        
        excel_data = create_excel_file(data)
        
        response = client.post(
            "/api/productos/bulk-upload",
            files={"file": ("productos.xlsx", excel_data, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")}
        )
        
        assert response.status_code == 201
        result = response.json()
        
        assert result["total_rows"] == 2
        assert result["successful"] == 1
        assert result["failed"] == 1
        assert len(result["errors"]) == 1

    def test_bulk_upload_campos_faltantes(self, client):
        """Test con campos requeridos faltantes"""
        data = [{
            "nombre": "Producto Test"
            # Faltan campos requeridos
        }]
        
        excel_data = create_excel_file(data)
        
        response = client.post(
            "/api/productos/bulk-upload",
            files={"file": ("productos.xlsx", excel_data, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")}
        )
        
        assert response.status_code == 400
        assert "Columnas requeridas faltantes" in response.json()["detail"]

    @patch('services.productos_service.ProductosService._verificar_proveedor_activo')
    def test_bulk_upload_con_duplicados(self, mock_verificar, client):
        """Test con filas duplicadas"""
        proveedor_id = str(uuid4())
        mock_verificar.return_value = {"id": proveedor_id, "nombre": "Proveedor Test"}
        
        data = [
            {
                "nombre": "Paracetamol 500mg",
                "categoria": "MEDICAMENTOS",
                "precio_unitario": 15.50,
                "proveedor_id": proveedor_id,
                "sku": "MED-001"
            },
            {
                "nombre": "Paracetamol 500mg",  # Duplicado
                "categoria": "MEDICAMENTOS",
                "precio_unitario": 15.50,
                "proveedor_id": proveedor_id,
                "sku": "MED-001"
            }
        ]
        
        excel_data = create_excel_file(data)
        
        response = client.post(
            "/api/productos/bulk-upload",
            files={"file": ("productos.xlsx", excel_data, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")}
        )
        
        assert response.status_code == 201
        result = response.json()
        
        assert result["total_rows"] == 2
        assert result["successful"] == 1
        assert result["skipped_duplicates"] == 1
        assert len(result["duplicate_rows"]) == 1

    @patch('services.productos_service.ProductosService._verificar_proveedor_activo')
    def test_bulk_upload_actualizar_existente(self, mock_verificar, client, test_db):
        """Test actualizar producto existente"""
        from models.producto import Producto
        
        proveedor_id = uuid4()
        mock_verificar.return_value = {"id": str(proveedor_id), "nombre": "Proveedor Test"}
        
        # Crear producto existente
        producto_existente = Producto(
            nombre="Producto Original",
            descripcion="Desc original",
            categoria="MEDICAMENTOS",
            imagen_url=None,
            precio_unitario=10.00,
            disponible=True,
            unidad_medida="UNIDAD",
            sku="MED-EXIST",
            tipo_almacenamiento="AMBIENTE",
            proveedor_id=proveedor_id,
            proveedor_nombre="Proveedor Test"
        )
        test_db.add(producto_existente)
        test_db.commit()
        
        # Actualizar con Excel
        data = [{
            "nombre": "Producto Actualizado",
            "categoria": "MEDICAMENTOS",
            "precio_unitario": 20.00,
            "proveedor_id": str(proveedor_id),
            "sku": "MED-EXIST"  # Mismo SKU
        }]
        
        excel_data = create_excel_file(data)
        
        response = client.post(
            "/api/productos/bulk-upload",
            files={"file": ("productos.xlsx", excel_data, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")}
        )
        
        assert response.status_code == 201
        result = response.json()
        
        assert result["successful"] == 1
        assert result["created"] == 0
        assert result["updated"] == 1
        assert len(result["updated_products"]) == 1


class TestBulkUploadValidacionEstructura:
    """Tests de validación de estructura del archivo"""

    def test_archivo_vacio(self, client):
        """Test con archivo Excel vacío"""
        data = []
        excel_data = create_excel_file(data)
        
        response = client.post(
            "/api/productos/bulk-upload",
            files={"file": ("productos.xlsx", excel_data, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")}
        )
        
        assert response.status_code == 400
        assert "vacío" in response.json()["detail"]

    def test_columnas_incorrectas(self, client):
        """Test con columnas incorrectas"""
        data = [{
            "columna_incorrecta": "valor",
            "otra_columna": "otro valor"
        }]
        
        excel_data = create_excel_file(data)
        
        response = client.post(
            "/api/productos/bulk-upload",
            files={"file": ("productos.xlsx", excel_data, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")}
        )
        
        assert response.status_code == 400
        detail = response.json()["detail"]
        assert "Columnas requeridas faltantes" in detail

    @patch('services.productos_service.ProductosService._verificar_proveedor_activo')
    def test_valores_por_defecto(self, mock_verificar, client):
        """Test que los valores por defecto se aplican correctamente"""
        proveedor_id = str(uuid4())
        mock_verificar.return_value = {"id": proveedor_id, "nombre": "Proveedor Test"}
        
        data = [{
            "nombre": "Producto Mínimo",
            "categoria": "MEDICAMENTOS",
            "precio_unitario": 15.50,
            "proveedor_id": proveedor_id,
            "sku": "MIN-001"
            # Sin campos opcionales
        }]
        
        excel_data = create_excel_file(data)
        
        response = client.post(
            "/api/productos/bulk-upload",
            files={"file": ("productos.xlsx", excel_data, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")}
        )
        
        assert response.status_code == 201
        result = response.json()
        assert result["successful"] == 1

