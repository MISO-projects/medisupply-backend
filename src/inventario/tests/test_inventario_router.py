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
        mock_inventory_service.listar_registros_paginados.assert_called_once_with(
            skip=0, 
            limit=10,
            text_search=None,
            categoria=None,
            estado=None
        )

    def test_crear_registro(self, client: TestClient, mock_inventory_service: Mock, mock_current_user: dict):
        """Test: Endpoint POST /api/inventario/ con autenticación"""
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
        
        # Verificar que el servicio fue llamado con los parámetros correctos
        call_args = mock_inventory_service.crear_registro_inventario.call_args
        assert call_args is not None
        # El primer argumento es el schema
        assert call_args[0][0].lote == "LOTE-123"
        # Los argumentos con nombre incluyen usuario_id e ip_origen
        assert call_args[1]["usuario_id"] == mock_current_user["sub"]
        assert "ip_origen" in call_args[1]

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

    def test_actualizar_registro(self, client: TestClient, mock_inventory_service: Mock, mock_current_user: dict):
        """Test: Endpoint PUT /api/inventario/{inventario_id} con autenticación"""
        inventario_id = str(uuid4())
        payload = {
            "cantidad": 150,
            "ubicacion": "BODEGA-B"
        }
        
        mock_response_data = {
            "id": inventario_id,
            "producto_id": str(uuid4()),
            "lote": "LOTE-123",
            "fecha_vencimiento": "2026-10-30",
            "cantidad": 150,
            "ubicacion": "BODEGA-B",
            "estado": "DISPONIBLE",
            "fecha_recepcion": "2025-10-30T10:00:00Z",
            "created_at": "2025-10-30T10:00:00Z",
            "updated_at": "2025-11-17T10:00:00Z"
        }
        mock_inventory_service.actualizar_registro_inventario.return_value = mock_response_data
        
        response = client.put(f"/api/inventario/{inventario_id}", json=payload)
        
        assert response.status_code == 200
        assert response.json()["cantidad"] == 150
        assert response.json()["ubicacion"] == "BODEGA-B"
        
        # Verificar que el servicio fue llamado con los parámetros correctos
        call_args = mock_inventory_service.actualizar_registro_inventario.call_args
        assert call_args is not None
        assert call_args[1]["inventario_id"] == inventario_id
        assert call_args[1]["usuario_id"] == mock_current_user["sub"]
        assert "ip_origen" in call_args[1]

    def test_eliminar_registro(self, client: TestClient, mock_inventory_service: Mock, mock_current_user: dict):
        """Test: Endpoint DELETE /api/inventario/{inventario_id} con autenticación"""
        inventario_id = str(uuid4())
        
        mock_response_data = {
            "message": f"Registro de inventario {inventario_id} eliminado correctamente"
        }
        mock_inventory_service.eliminar_registro_inventario.return_value = mock_response_data
        
        response = client.delete(f"/api/inventario/{inventario_id}")
        
        assert response.status_code == 200
        assert "eliminado correctamente" in response.json()["message"]
        
        # Verificar que el servicio fue llamado con los parámetros correctos
        call_args = mock_inventory_service.eliminar_registro_inventario.call_args
        assert call_args is not None
        assert call_args[1]["inventario_id"] == inventario_id
        assert call_args[1]["usuario_id"] == mock_current_user["sub"]
        assert "ip_origen" in call_args[1]

    def test_actualizar_registro_not_found(self, client: TestClient, mock_inventory_service: Mock):
        """Test: Error 404 al actualizar un registro inexistente"""
        from fastapi import HTTPException
        inventario_id = str(uuid4())
        payload = {"cantidad": 150}
        
        mock_inventory_service.actualizar_registro_inventario.side_effect = HTTPException(
            status_code=404,
            detail="Registro de inventario no encontrado"
        )
        
        response = client.put(f"/api/inventario/{inventario_id}", json=payload)
        
        assert response.status_code == 404

    def test_eliminar_registro_not_found(self, client: TestClient, mock_inventory_service: Mock):
        """Test: Error 404 al eliminar un registro inexistente"""
        from fastapi import HTTPException
        inventario_id = str(uuid4())
        
        mock_inventory_service.eliminar_registro_inventario.side_effect = HTTPException(
            status_code=404,
            detail="Registro de inventario no encontrado"
        )
        
        response = client.delete(f"/api/inventario/{inventario_id}")
        
        assert response.status_code == 404