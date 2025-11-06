import pytest
import io
import pandas as pd
from uuid import uuid4
from unittest.mock import AsyncMock, patch, MagicMock
from fastapi import UploadFile, HTTPException

from models.producto import Producto
from services.productos_service import ProductosService
from schemas.producto_schema import BulkUploadResponse

pytestmark = pytest.mark.asyncio


def create_excel_file(data):
    """Helper para crear un archivo Excel en memoria"""
    df = pd.DataFrame(data)
    output = io.BytesIO()
    df.to_excel(output, index=False, engine='openpyxl')
    output.seek(0)
    return output


def create_upload_file(excel_bytes, filename="test.xlsx"):
    """Helper para crear un UploadFile mock"""
    upload_file = MagicMock(spec=UploadFile)
    upload_file.filename = filename
    upload_file.content_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    upload_file.read = AsyncMock(return_value=excel_bytes.getvalue())
    upload_file.seek = AsyncMock()
    return upload_file


class TestBulkUploadBasic:
    """Tests básicos de validación"""

    async def test_archivo_vacio(self, test_db):
        """Test con archivo Excel vacío"""
        service = ProductosService(test_db)
        
        excel_data = create_excel_file([])
        upload_file = create_upload_file(excel_data)
        
        with pytest.raises(HTTPException) as exc_info:
            await service.bulk_upload_productos(upload_file)
        
        assert exc_info.value.status_code == 400
        assert "vacío" in str(exc_info.value.detail)

    async def test_columnas_faltantes(self, test_db):
        """Test con columnas requeridas faltantes"""
        service = ProductosService(test_db)
        
        data = [{
            "nombre": "Producto Test",
            # Falta categoria, precio_unitario, proveedor_id
        }]
        
        excel_data = create_excel_file(data)
        upload_file = create_upload_file(excel_data)
        
        with pytest.raises(HTTPException) as exc_info:
            await service.bulk_upload_productos(upload_file)
        
        assert exc_info.value.status_code == 400
        assert "Columnas requeridas faltantes" in str(exc_info.value.detail)

    async def test_campos_requeridos_vacios(self, test_db):
        """Test con campos requeridos vacíos"""
        service = ProductosService(test_db)
        proveedor_id = str(uuid4())
        
        data = [{
            "nombre": "",  # Vacío
            "categoria": "MEDICAMENTOS",
            "precio_unitario": 10.0,
            "proveedor_id": proveedor_id
        }]
        
        excel_data = create_excel_file(data)
        upload_file = create_upload_file(excel_data)
        
        with pytest.raises(HTTPException) as exc_info:
            await service.bulk_upload_productos(upload_file)
        
        assert exc_info.value.status_code == 400
        detail = exc_info.value.detail
        assert detail["message"] == "Campos requeridos faltantes en algunas filas"
        assert len(detail["missing_data"]) == 1
        assert "nombre" in detail["missing_data"][0]["missing_fields"]


class TestBulkUploadCreacion:
    """Tests de creación de productos"""

    @patch('services.productos_service.ProductosService._verificar_proveedor_activo')
    async def test_crear_producto_simple(self, mock_verificar, test_db):
        """Test crear un producto nuevo simple"""
        proveedor_id = str(uuid4())
        mock_verificar.return_value = {"id": proveedor_id, "nombre": "Proveedor Test"}
        
        service = ProductosService(test_db)
        
        data = [{
            "nombre": "Paracetamol 500mg",
            "descripcion": "Analgésico",
            "categoria": "MEDICAMENTOS",
            "precio_unitario": 15.50,
            "proveedor_id": proveedor_id,
            "sku": "MED-001"
        }]
        
        excel_data = create_excel_file(data)
        upload_file = create_upload_file(excel_data)
        
        result = await service.bulk_upload_productos(upload_file)
        
        assert result.total_rows == 1
        assert result.successful == 1
        assert result.created == 1
        assert result.updated == 0
        assert result.failed == 0
        assert len(result.created_products) == 1
        
        # Verificar que el producto fue creado en la BD
        producto = test_db.query(Producto).filter(Producto.sku == "MED-001").first()
        assert producto is not None
        assert producto.nombre == "Paracetamol 500mg"
        assert float(producto.precio_unitario) == 15.50

    @patch('services.productos_service.ProductosService._verificar_proveedor_activo')
    async def test_crear_multiples_productos(self, mock_verificar, test_db):
        """Test crear múltiples productos"""
        proveedor_id = str(uuid4())
        mock_verificar.return_value = {"id": proveedor_id, "nombre": "Proveedor Test"}
        
        service = ProductosService(test_db)
        
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
            },
            {
                "nombre": "Aspirina 100mg",
                "categoria": "MEDICAMENTOS",
                "precio_unitario": 12.00,
                "proveedor_id": proveedor_id,
                "sku": "MED-003"
            }
        ]
        
        excel_data = create_excel_file(data)
        upload_file = create_upload_file(excel_data)
        
        result = await service.bulk_upload_productos(upload_file)
        
        assert result.total_rows == 3
        assert result.successful == 3
        assert result.created == 3
        assert result.updated == 0
        assert result.failed == 0
        assert len(result.created_products) == 3
        
        # Verificar que todos fueron creados
        productos = test_db.query(Producto).all()
        assert len(productos) == 3

    @patch('services.productos_service.ProductosService._verificar_proveedor_activo')
    async def test_crear_producto_sin_sku(self, mock_verificar, test_db):
        """Test crear producto sin SKU (debe auto-generarse)"""
        proveedor_id = str(uuid4())
        mock_verificar.return_value = {"id": proveedor_id, "nombre": "Proveedor Test"}
        
        service = ProductosService(test_db)
        
        data = [{
            "nombre": "Paracetamol 500mg",
            "categoria": "MEDICAMENTOS",
            "precio_unitario": 15.50,
            "proveedor_id": proveedor_id
            # Sin SKU
        }]
        
        excel_data = create_excel_file(data)
        upload_file = create_upload_file(excel_data)
        
        result = await service.bulk_upload_productos(upload_file)
        
        assert result.successful == 1
        assert result.created == 1
        
        # Verificar que se generó un SKU
        producto = test_db.query(Producto).first()
        assert producto is not None
        assert producto.sku is not None
        assert producto.sku.startswith("PRD-")


class TestBulkUploadActualizacion:
    """Tests de actualización de productos existentes"""

    @patch('services.productos_service.ProductosService._verificar_proveedor_activo')
    async def test_actualizar_producto_existente(self, mock_verificar, test_db):
        """Test actualizar un producto existente por SKU"""
        proveedor_id = uuid4()
        mock_verificar.return_value = {"id": str(proveedor_id), "nombre": "Proveedor Test"}
        
        # Crear producto existente
        producto_existente = Producto(
            nombre="Paracetamol 500mg",
            descripcion="Descripción vieja",
            categoria="MEDICAMENTOS",
            imagen_url=None,
            precio_unitario=10.00,
            disponible=True,
            unidad_medida="UNIDAD",
            sku="MED-001",
            tipo_almacenamiento="AMBIENTE",
            proveedor_id=proveedor_id,
            proveedor_nombre="Proveedor Test"
        )
        test_db.add(producto_existente)
        test_db.commit()
        
        service = ProductosService(test_db)
        
        # Actualizar con nuevos datos
        data = [{
            "nombre": "Paracetamol 500mg ACTUALIZADO",
            "descripcion": "Nueva descripción",
            "categoria": "MEDICAMENTOS",
            "precio_unitario": 20.00,
            "proveedor_id": str(proveedor_id),
            "sku": "MED-001"  # Mismo SKU
        }]
        
        excel_data = create_excel_file(data)
        upload_file = create_upload_file(excel_data)
        
        result = await service.bulk_upload_productos(upload_file)
        
        assert result.total_rows == 1
        assert result.successful == 1
        assert result.created == 0
        assert result.updated == 1
        assert len(result.updated_products) == 1
        
        # Verificar que fue actualizado
        test_db.refresh(producto_existente)
        assert producto_existente.nombre == "Paracetamol 500mg ACTUALIZADO"
        assert producto_existente.descripcion == "Nueva descripción"
        assert float(producto_existente.precio_unitario) == 20.00

    @patch('services.productos_service.ProductosService._verificar_proveedor_activo')
    async def test_mezcla_crear_y_actualizar(self, mock_verificar, test_db):
        """Test mezcla de creación y actualización"""
        proveedor_id = uuid4()
        mock_verificar.return_value = {"id": str(proveedor_id), "nombre": "Proveedor Test"}
        
        # Crear producto existente
        producto_existente = Producto(
            nombre="Producto Existente",
            descripcion="Desc",
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
        
        service = ProductosService(test_db)
        
        data = [
            {
                "nombre": "Producto Existente ACTUALIZADO",
                "categoria": "MEDICAMENTOS",
                "precio_unitario": 20.00,
                "proveedor_id": str(proveedor_id),
                "sku": "MED-EXIST"  # Actualizar
            },
            {
                "nombre": "Producto Nuevo",
                "categoria": "INSUMOS",
                "precio_unitario": 15.00,
                "proveedor_id": str(proveedor_id),
                "sku": "INS-NEW"  # Crear
            }
        ]
        
        excel_data = create_excel_file(data)
        upload_file = create_upload_file(excel_data)
        
        result = await service.bulk_upload_productos(upload_file)
        
        assert result.total_rows == 2
        assert result.successful == 2
        assert result.created == 1
        assert result.updated == 1
        assert len(result.created_products) == 1
        assert len(result.updated_products) == 1


class TestBulkUploadDuplicados:
    """Tests de manejo de duplicados"""

    @patch('services.productos_service.ProductosService._verificar_proveedor_activo')
    async def test_duplicados_en_archivo(self, mock_verificar, test_db):
        """Test con filas duplicadas en el mismo archivo"""
        proveedor_id = str(uuid4())
        mock_verificar.return_value = {"id": proveedor_id, "nombre": "Proveedor Test"}
        
        service = ProductosService(test_db)
        
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
            },
            {
                "nombre": "Paracetamol 500mg",  # Duplicado
                "categoria": "MEDICAMENTOS",
                "precio_unitario": 15.50,
                "proveedor_id": proveedor_id,
                "sku": "MED-001"  # Mismo SKU
            }
        ]
        
        excel_data = create_excel_file(data)
        upload_file = create_upload_file(excel_data)
        
        result = await service.bulk_upload_productos(upload_file)
        
        assert result.total_rows == 3
        assert result.successful == 2
        assert result.skipped_duplicates == 1
        assert len(result.duplicate_rows) == 1
        assert 4 in result.duplicate_rows  # Fila 4 (índice 2 + 2 por header)
        
        # Solo 2 productos deben estar en la BD
        productos = test_db.query(Producto).all()
        assert len(productos) == 2


class TestBulkUploadErrores:
    """Tests de manejo de errores"""

    async def test_proveedor_invalido(self, test_db):
        """Test con proveedor_id inválido"""
        service = ProductosService(test_db)
        
        data = [{
            "nombre": "Paracetamol 500mg",
            "categoria": "MEDICAMENTOS",
            "precio_unitario": 15.50,
            "proveedor_id": "invalid-uuid",
            "sku": "MED-001"
        }]
        
        excel_data = create_excel_file(data)
        upload_file = create_upload_file(excel_data)
        
        result = await service.bulk_upload_productos(upload_file)
        
        assert result.total_rows == 1
        assert result.successful == 0
        assert result.failed == 1
        assert len(result.errors) == 1
        assert "proveedor_id inválido" in result.errors[0].error

    @patch('services.productos_service.ProductosService._verificar_proveedor_activo')
    async def test_proveedor_no_encontrado(self, mock_verificar, test_db):
        """Test con proveedor que no existe"""
        proveedor_id = str(uuid4())
        mock_verificar.side_effect = HTTPException(status_code=404, detail="Proveedor no encontrado")
        
        service = ProductosService(test_db)
        
        data = [{
            "nombre": "Paracetamol 500mg",
            "categoria": "MEDICAMENTOS",
            "precio_unitario": 15.50,
            "proveedor_id": proveedor_id,
            "sku": "MED-001"
        }]
        
        excel_data = create_excel_file(data)
        upload_file = create_upload_file(excel_data)
        
        result = await service.bulk_upload_productos(upload_file)
        
        assert result.total_rows == 1
        assert result.successful == 0
        assert result.failed == 1
        assert "Proveedor no encontrado" in result.errors[0].error

    @patch('services.productos_service.ProductosService._verificar_proveedor_activo')
    async def test_precio_invalido(self, mock_verificar, test_db):
        """Test con precio inválido"""
        proveedor_id = str(uuid4())
        mock_verificar.return_value = {"id": proveedor_id, "nombre": "Proveedor Test"}
        
        service = ProductosService(test_db)
        
        data = [{
            "nombre": "Paracetamol 500mg",
            "categoria": "MEDICAMENTOS",
            "precio_unitario": -10.00,  # Precio negativo
            "proveedor_id": proveedor_id,
            "sku": "MED-001"
        }]
        
        excel_data = create_excel_file(data)
        upload_file = create_upload_file(excel_data)
        
        result = await service.bulk_upload_productos(upload_file)
        
        assert result.total_rows == 1
        assert result.successful == 0
        assert result.failed == 1
        assert "precio_unitario inválido" in result.errors[0].error

    @patch('services.productos_service.ProductosService._verificar_proveedor_activo')
    async def test_errores_parciales(self, mock_verificar, test_db):
        """Test con algunos productos válidos y otros con errores"""
        proveedor_id = str(uuid4())
        mock_verificar.return_value = {"id": proveedor_id, "nombre": "Proveedor Test"}
        
        service = ProductosService(test_db)
        
        data = [
            {
                "nombre": "Producto Válido 1",
                "categoria": "MEDICAMENTOS",
                "precio_unitario": 15.50,
                "proveedor_id": proveedor_id,
                "sku": "MED-001"
            },
            {
                "nombre": "Producto Inválido",
                "categoria": "MEDICAMENTOS",
                "precio_unitario": -10.00,  # Error
                "proveedor_id": proveedor_id,
                "sku": "MED-002"
            },
            {
                "nombre": "Producto Válido 2",
                "categoria": "INSUMOS",
                "precio_unitario": 20.00,
                "proveedor_id": proveedor_id,
                "sku": "INS-001"
            }
        ]
        
        excel_data = create_excel_file(data)
        upload_file = create_upload_file(excel_data)
        
        result = await service.bulk_upload_productos(upload_file)
        
        assert result.total_rows == 3
        assert result.successful == 2
        assert result.failed == 1
        assert len(result.created_products) == 2
        assert len(result.errors) == 1


class TestBulkUploadCamposOpcionales:
    """Tests de campos opcionales y valores por defecto"""

    @patch('services.productos_service.ProductosService._verificar_proveedor_activo')
    async def test_campos_opcionales_vacios(self, mock_verificar, test_db):
        """Test con campos opcionales vacíos (deben usar defaults)"""
        proveedor_id = str(uuid4())
        mock_verificar.return_value = {"id": proveedor_id, "nombre": "Proveedor Test"}
        
        service = ProductosService(test_db)
        
        data = [{
            "nombre": "Paracetamol 500mg",
            "categoria": "MEDICAMENTOS",
            "precio_unitario": 15.50,
            "proveedor_id": proveedor_id,
            "sku": "MED-001"
            # Sin descripcion, imagen_url, disponible, unidad_medida, tipo_almacenamiento, observaciones
        }]
        
        excel_data = create_excel_file(data)
        upload_file = create_upload_file(excel_data)
        
        result = await service.bulk_upload_productos(upload_file)
        
        assert result.successful == 1
        
        producto = test_db.query(Producto).first()
        assert producto.disponible == True  # Default
        assert producto.unidad_medida == "UNIDAD"  # Default
        assert producto.tipo_almacenamiento == "AMBIENTE"  # Default

    @patch('services.productos_service.ProductosService._verificar_proveedor_activo')
    async def test_disponible_valores(self, mock_verificar, test_db):
        """Test diferentes valores para campo disponible"""
        proveedor_id = str(uuid4())
        mock_verificar.return_value = {"id": proveedor_id, "nombre": "Proveedor Test"}
        
        service = ProductosService(test_db)
        
        data = [
            {"nombre": "Prod1", "categoria": "MED", "precio_unitario": 10, "proveedor_id": proveedor_id, "sku": "S1", "disponible": "true"},
            {"nombre": "Prod2", "categoria": "MED", "precio_unitario": 10, "proveedor_id": proveedor_id, "sku": "S2", "disponible": "1"},
            {"nombre": "Prod3", "categoria": "MED", "precio_unitario": 10, "proveedor_id": proveedor_id, "sku": "S3", "disponible": "si"},
            {"nombre": "Prod4", "categoria": "MED", "precio_unitario": 10, "proveedor_id": proveedor_id, "sku": "S4", "disponible": "false"},
            {"nombre": "Prod5", "categoria": "MED", "precio_unitario": 10, "proveedor_id": proveedor_id, "sku": "S5", "disponible": "0"},
        ]
        
        excel_data = create_excel_file(data)
        upload_file = create_upload_file(excel_data)
        
        result = await service.bulk_upload_productos(upload_file)
        
        assert result.successful == 5
        
        productos = test_db.query(Producto).order_by(Producto.sku).all()
        assert productos[0].disponible == True  # "true"
        assert productos[1].disponible == True  # "1"
        assert productos[2].disponible == True  # "si"
        assert productos[3].disponible == False  # "false"
        assert productos[4].disponible == False  # "0"

