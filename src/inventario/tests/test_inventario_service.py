# src/inventario/tests/test_inventario_service.py

import pytest
from unittest.mock import Mock, patch, AsyncMock
from sqlalchemy.orm import Session
from datetime import date, timedelta
from uuid import uuid4

from services.inventario_service import InventarioService
from db.inventario_model import Inventario
from schemas.inventario_schema import CrearRegistroInventarioSchema
from fastapi import HTTPException

pytestmark = pytest.mark.asyncio

class TestInventarioService:

    @pytest.fixture
    def mock_db(self):
        """Fixture de un mock de la sesión de BBDD"""
        return Mock(spec=Session)

    @pytest.fixture
    def service(self, mock_db: Mock):
        """
        Fixture del servicio. Solo necesita la BBDD mockeada.
        Parcheamos 'get_redis_client' que es llamado DENTRO del __init__.
        """
        with patch('services.inventario_service.get_redis_client') as mock_get_redis:
            mock_redis = Mock()
            mock_redis.client = Mock()
            mock_get_redis.return_value = mock_redis
            service_instance = InventarioService(db=mock_db)
            yield service_instance 

    def test_crear_registro_inventario_success(self, service: InventarioService, mock_db: Mock):
        """Test: Crear un registro de inventario exitosamente (con mock DB)"""
        data = CrearRegistroInventarioSchema(
            producto_id=uuid4(),
            lote="LOTE-123",
            fecha_vencimiento=date.today() + timedelta(days=30),
            cantidad=100
        )
        
        mock_inventario = Mock(spec=Inventario)
        mock_inventario.to_dict.return_value = {"id": str(uuid4()), "lote": "LOTE-123"}
        mock_db.refresh.side_effect = lambda x: setattr(x, 'to_dict', mock_inventario.to_dict)

        resultado = service.crear_registro_inventario(data)
        
        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()
        assert resultado["lote"] == "LOTE-123"

    @patch("services.inventario_service.httpx.AsyncClient")
    async def test_listar_registros_paginados(self, mock_http_client: Mock, service: InventarioService, mock_db: Mock):
        """Test: Listar y enriquecer registros (mockeando httpx y db)"""
        
        prod_id_1 = str(uuid4())
        mock_registro = Inventario(producto_id=prod_id_1, lote="L1", fecha_vencimiento=date.today(), cantidad=100)
        mock_registro.to_dict = Mock(return_value={"producto_id": prod_id_1, "lote": "L1"})

        mock_db.query.return_value.count.return_value = 1
        mock_db.query.return_value.order_by.return_value.offset.return_value.limit.return_value.all.return_value = [mock_registro]

        mock_async_client = mock_http_client.return_value.__aenter__.return_value
        mock_response = Mock(status_code=200)
        mock_response.json.return_value = {
            "detalles": {
                prod_id_1: {"nombre": "Producto Test", "sku": "SKU-123"}
            }
        }
        mock_async_client.post.return_value = mock_response
        
        registros, total = await service.listar_registros_paginados(skip=0, limit=10)
        
        assert total == 1
        assert len(registros) == 1
        assert registros[0]["lote"] == "L1"
        assert registros[0]["producto_nombre"] == "Producto Test"

    def test_get_stock_agregado_por_ids(self, service: InventarioService, mock_db: Mock):
        """Test: Lógica de suma de stock (mockeando la BBDD)"""
        prod_id_1 = str(uuid4())
        prod_id_2 = str(uuid4())
        
        mock_query_result = [(prod_id_1, 150), (prod_id_2, 25)]
        
        mock_db.query.return_value.filter.return_value.group_by.return_value.all.return_value = mock_query_result
        
        resultado = service.get_stock_agregado_por_ids([prod_id_1, prod_id_2])
        
        assert resultado[prod_id_1] == 150
        assert resultado[prod_id_2] == 25