# src/inventario/tests/test_inventario_router.py

import pytest
from unittest.mock import Mock, AsyncMock
from fastapi.testclient import TestClient
from uuid import uuid4

from schemas.inventario_schema import CrearRegistroInventarioSchema, StockBatchRequest

class TestInventarioRouter:

    @pytest.mark.asyncio
    async def test_get_registros_inventario_paginado(self, client: TestClient, mock_inventory_service: Mock):
        """Test: Endpoint GET /api/inventario/ (async)"""
        
        mock_item = {
            "id": str(uuid4()),
            "producto_id": str(uuid4()),
            "lote": "LOTE-MOCK",
            "fecha_vencimiento": "2026-10-30",
            "cantidad": 100,
            "ubicacion": "BODEGA-MOCK",
            "temperatura_requerida": "AMBIENTE",
            "estado": "DISPONIBLE",
            "condiciones_especiales": None,
            "observaciones": None,
            "fecha_recepcion": "2025-10-30T10:00:00Z",
            "created_at": "2025-10-30T10:00:00Z",
            "updated_at": None,
            "producto_nombre": "Test",
            "producto_sku": "SKU-123"
        }
        mock_inventory_service.listar_registros_paginados.return_value = (
            [mock_item], 1
        )
        
       
        response = client.get("/api/inventario/?page=1&page_size=10")
        
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert data["items"][0]["producto_nombre"] == "Test"
        mock_inventory_service.listar_registros_paginados.assert_called_once_with(skip=0, limit=10)

    def test_crear_registro(self, client: TestClient, mock_inventory_service: Mock):
        """Test: Endpoint POST /api/inventario/ (sync)"""
        payload = {
            "producto_id": str(uuid4()),
            "lote": "LOTE-123",
            "fecha_vencimiento": "2026-10-30",
            "cantidad": 100
        }
        
        mock_response_data = {
            "id": str(uuid4()),
            **payload,
            "fecha_recepcion": "2025-10-30T10:00:00Z",
            "created_at": "2025-10-30T10:00:00Z",
            "updated_at": None,
            "producto_nombre": "Test", 
            "producto_sku": "SKU-123"
        }
        mock_inventory_service.crear_registro_inventario.return_value = mock_response_data
      
        response = client.post("/api/inventario/", json=payload)
        
        assert response.status_code == 201
        assert response.json()["lote"] == "LOTE-123"
        mock_inventory_service.crear_registro_inventario.assert_called_once_with(
            CrearRegistroInventarioSchema(**payload)
        )

    def test_get_stock_batch(self, client: TestClient, mock_inventory_service: Mock):
        """Test: Endpoint POST /api/inventario/stock/batch (sync)"""
        prod_id = str(uuid4())
        payload = {"producto_ids": [prod_id]}
        
        mock_inventory_service.get_stock_agregado_por_ids.return_value = {
            prod_id: 150
        }
        
        response = client.post("/api/inventario/stock/batch", json=payload)
        
        assert response.status_code == 200
        data = response.json()
        assert data["stock_data"][prod_id] == 150
        mock_inventory_service.get_stock_agregado_por_ids.assert_called_once_with(
            [prod_id]
        )