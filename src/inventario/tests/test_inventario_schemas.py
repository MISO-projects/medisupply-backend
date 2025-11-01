# src/inventario/tests/test_inventario_schemas.py

import pytest
from pydantic import ValidationError
from uuid import uuid4
from datetime import date, datetime

from schemas.inventario_schema import (
    CrearRegistroInventarioSchema, 
    StockBatchRequest,
    RegistroInventarioResponseSchema,
    InventarioListResponse,
    StockBatchResponse,
    StockDisponibleResponse
)

class TestRequestSchemas:
    """Prueba los schemas de Pydantic para los 'requests' (entradas)"""

    def test_crear_registro_inventario_schema_valid(self):
        """Test: Creación válida de schema de registro"""
        data = {
            "producto_id": uuid4(),
            "lote": "LOTE-123",
            "fecha_vencimiento": "2026-10-30",
            "cantidad": 100
        }
        schema = CrearRegistroInventarioSchema(**data)
        assert schema.producto_id == data["producto_id"]
        assert schema.lote == "LOTE-123"
        assert schema.cantidad == 100
        assert schema.ubicacion == "BODEGA-PRINCIPAL"

    def test_crear_registro_inventario_schema_invalid(self):
        """Test: Falla si faltan campos requeridos"""
        with pytest.raises(ValidationError) as e:
            CrearRegistroInventarioSchema(lote="LOTE-123", cantidad=100) 
        
        errors = e.value.errors()
        assert any(err['loc'] == ('producto_id',) and err['type'] == 'missing' for err in errors)
        assert any(err['loc'] == ('fecha_vencimiento',) and err['type'] == 'missing' for err in errors)

    def test_crear_registro_inventario_cantidad_invalida(self):
        """Test: Falla si la cantidad es negativa (menor que 0)"""
        with pytest.raises(ValidationError):
            CrearRegistroInventarioSchema(
                producto_id=uuid4(),
                lote="LOTE-INVALIDO",
                fecha_vencimiento=date.today(),
                cantidad=-1
            )

    def test_stock_batch_request_schema(self):
        """Test: Schema de solicitud de stock en lote"""
        data = {"producto_ids": [str(uuid4()), str(uuid4())]}
        schema = StockBatchRequest(**data)
        assert len(schema.producto_ids) == 2
        
        with pytest.raises(ValidationError):
            StockBatchRequest()

class TestResponseSchemas:
    """Prueba los schemas de Pydantic para los 'responses' (salidas)"""

    def test_registro_inventario_response_schema_valid(self):
        """Test: Creación válida del response schema (con enriquecimiento)"""
        data = {
            "id": uuid4(),
            "producto_id": uuid4(),
            "lote": "LOTE-123",
            "fecha_vencimiento": "2026-10-30",
            "cantidad": 100,
            "fecha_recepcion": datetime.now(),
            "created_at": datetime.now(),
            "updated_at": None,
            "producto_nombre": "Producto Test",
            "producto_sku": "SKU-123"
        }
        schema = RegistroInventarioResponseSchema(**data)
        assert schema.lote == "LOTE-123"
        assert schema.producto_nombre == "Producto Test"

    def test_registro_inventario_response_schema_sin_enriquecimiento(self):
        """Test: Los campos de enriquecimiento deben ser opcionales (default=None)"""
        data = {
            "id": uuid4(),
            "producto_id": uuid4(),
            "lote": "LOTE-123",
            "fecha_vencimiento": "2026-10-30",
            "cantidad": 100,
            "fecha_recepcion": datetime.now(),
            "created_at": datetime.now(),
            "updated_at": None
        }
        schema = RegistroInventarioResponseSchema(**data)
        assert schema.producto_nombre is None
        assert schema.producto_sku is None

    def test_inventario_list_response_schema_valid(self):
        """Test: Creación válida de la respuesta de lista paginada"""
        item_data = {
            "id": uuid4(),
            "producto_id": uuid4(),
            "lote": "LOTE-123",
            "fecha_vencimiento": "2026-10-30",
            "cantidad": 100,
            "fecha_recepcion": datetime.now(),
            "created_at": datetime.now(),
            "updated_at": None,
            "producto_nombre": "Producto Test",
            "producto_sku": "SKU-123"
        }
        response_data = {
            "items": [item_data],
            "total": 1,
            "page": 1,
            "page_size": 10,
            "total_pages": 1
        }
        schema = InventarioListResponse(**response_data)
        assert schema.total == 1
        assert len(schema.items) == 1

    def test_stock_batch_response_schema(self):
        """Test: Schema de respuesta de stock en lote"""
        id_1 = str(uuid4())
        data = {"stock_data": {id_1: 150}}
        schema = StockBatchResponse(**data)
        assert schema.stock_data[id_1] == 150