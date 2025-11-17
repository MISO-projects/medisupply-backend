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
        Parcheamos 'get_redis_client' y 'get_pubsub_service' que son llamados DENTRO del __init__.
        """
        with patch('services.inventario_service.get_redis_client') as mock_get_redis, \
             patch('services.inventario_service.get_pubsub_service') as mock_get_pubsub:
            
            # Mock Redis
            mock_redis = Mock()
            mock_redis.client = Mock()
            mock_get_redis.return_value = mock_redis
            
            # Mock PubSub
            mock_pubsub = Mock()
            mock_pubsub.publish_event = Mock(return_value=True)
            mock_get_pubsub.return_value = mock_pubsub
            
            service_instance = InventarioService(db=mock_db)
            yield service_instance 

    @pytest.mark.asyncio 
    async def test_crear_registro_inventario_success(self, service: InventarioService, mock_db: Mock):
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
    
        resultado = await service.crear_registro_inventario(data)
    
        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()
        mock_db.refresh.assert_called_once()
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

    @patch("services.inventario_service.httpx.AsyncClient")
    async def test_get_producto_ids_by_filters_text_search(self, mock_http_client: Mock, service: InventarioService):
        """Test: Obtener IDs de productos por text_search"""
        mock_async_client = mock_http_client.return_value.__aenter__.return_value
        mock_response = Mock(status_code=200)
        mock_response.json.return_value = {
            "producto_ids": ["prod-1", "prod-2"]
        }
        mock_async_client.post.return_value = mock_response
        
        resultado = await service._get_producto_ids_by_filters(text_search="Paracetamol")
        
        assert len(resultado) == 2
        assert "prod-1" in resultado
        assert "prod-2" in resultado
        mock_async_client.post.assert_called_once()
        call_args = mock_async_client.post.call_args
        assert call_args[1]["json"]["text_search"] == "Paracetamol"

    @patch("services.inventario_service.httpx.AsyncClient")
    async def test_get_producto_ids_by_filters_text_search_and_categoria(self, mock_http_client: Mock, service: InventarioService):
        """Test: Obtener IDs de productos por text_search y categoria"""
        mock_async_client = mock_http_client.return_value.__aenter__.return_value
        mock_response = Mock(status_code=200)
        mock_response.json.return_value = {
            "producto_ids": ["prod-1"]
        }
        mock_async_client.post.return_value = mock_response
        
        resultado = await service._get_producto_ids_by_filters(text_search="Paracetamol", categoria="MEDICAMENTOS")
        
        assert len(resultado) == 1
        assert "prod-1" in resultado
        call_args = mock_async_client.post.call_args
        assert call_args[1]["json"]["text_search"] == "Paracetamol"
        assert call_args[1]["json"]["categoria"] == "MEDICAMENTOS"

    @patch("services.inventario_service.httpx.AsyncClient")
    async def test_get_producto_ids_by_filters_no_filters(self, mock_http_client: Mock, service: InventarioService):
        """Test: Retornar lista vacía cuando no hay filtros"""
        resultado = await service._get_producto_ids_by_filters()
        
        assert resultado == []
        mock_http_client.assert_not_called()

    @patch("services.inventario_service.httpx.AsyncClient")
    async def test_listar_registros_paginados_text_search_producto(self, mock_http_client: Mock, service: InventarioService, mock_db: Mock):
        """Test: Listar registros filtrados por text_search en productos"""
        prod_id_1 = uuid4()
        prod_id_2 = uuid4()
        
        # Mock productos service response
        mock_async_client = mock_http_client.return_value.__aenter__.return_value
        mock_response = Mock(status_code=200)
        mock_response.json.return_value = {
            "producto_ids": [str(prod_id_1)]
        }
        mock_async_client.post.return_value = mock_response
        
        # Mock inventario records
        mock_registro = Mock(spec=Inventario)
        mock_registro.producto_id = prod_id_1
        mock_registro.to_dict.return_value = {
            "producto_id": str(prod_id_1),
            "lote": "L1",
            "ubicacion": "BODEGA-A"
        }
        
        # Mock DB query chain
        mock_query = Mock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.count.return_value = 1
        mock_query.order_by.return_value.offset.return_value.limit.return_value.all.return_value = [mock_registro]
        
        # Mock detalles productos
        mock_detalles_response = Mock(status_code=200)
        mock_detalles_response.json.return_value = {
            "detalles": {
                str(prod_id_1): {"nombre": "Paracetamol", "sku": "SKU-001"}
            }
        }
        mock_async_client.post.side_effect = [mock_response, mock_detalles_response]
        
        registros, total = await service.listar_registros_paginados(
            skip=0, limit=10, text_search="Paracetamol"
        )
        
        assert total == 1
        assert len(registros) == 1
        assert registros[0]["producto_nombre"] == "Paracetamol"
        assert registros[0]["producto_sku"] == "SKU-001"

    @patch("services.inventario_service.httpx.AsyncClient")
    async def test_listar_registros_paginados_text_search_ubicacion(self, mock_http_client: Mock, service: InventarioService, mock_db: Mock):
        """Test: Listar registros filtrados por text_search en ubicacion"""
        prod_id_1 = uuid4()
        
        # Mock productos service response (no matches)
        mock_async_client = mock_http_client.return_value.__aenter__.return_value
        mock_response = Mock(status_code=200)
        mock_response.json.return_value = {
            "producto_ids": []
        }
        mock_async_client.post.return_value = mock_response
        
        # Mock inventario record with matching ubicacion
        mock_registro = Mock(spec=Inventario)
        mock_registro.producto_id = prod_id_1
        mock_registro.to_dict.return_value = {
            "producto_id": str(prod_id_1),
            "lote": "L1",
            "ubicacion": "BODEGA-PRINCIPAL"
        }
        
        # Mock DB query chain
        mock_query = Mock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.count.return_value = 1
        mock_query.order_by.return_value.offset.return_value.limit.return_value.all.return_value = [mock_registro]
        
        # Mock detalles productos
        mock_detalles_response = Mock(status_code=200)
        mock_detalles_response.json.return_value = {
            "detalles": {
                str(prod_id_1): {"nombre": "Producto Test", "sku": "SKU-001"}
            }
        }
        mock_async_client.post.side_effect = [mock_response, mock_detalles_response]
        
        registros, total = await service.listar_registros_paginados(
            skip=0, limit=10, text_search="PRINCIPAL"
        )
        
        assert total == 1
        assert len(registros) == 1
        assert registros[0]["producto_nombre"] == "Producto Test"

    @patch("services.inventario_service.httpx.AsyncClient")
    async def test_listar_registros_paginados_categoria_only(self, mock_http_client: Mock, service: InventarioService, mock_db: Mock):
        """Test: Listar registros filtrados solo por categoria"""
        prod_id_1 = uuid4()
        
        # Mock productos service response
        mock_async_client = mock_http_client.return_value.__aenter__.return_value
        mock_response = Mock(status_code=200)
        mock_response.json.return_value = {
            "producto_ids": [str(prod_id_1)]
        }
        mock_async_client.post.return_value = mock_response
        
        # Mock inventario record
        mock_registro = Mock(spec=Inventario)
        mock_registro.producto_id = prod_id_1
        mock_registro.to_dict.return_value = {
            "producto_id": str(prod_id_1),
            "lote": "L1"
        }
        
        # Mock DB query chain
        mock_query = Mock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.count.return_value = 1
        mock_query.order_by.return_value.offset.return_value.limit.return_value.all.return_value = [mock_registro]
        
        # Mock detalles productos
        mock_detalles_response = Mock(status_code=200)
        mock_detalles_response.json.return_value = {
            "detalles": {
                str(prod_id_1): {"nombre": "Producto Test", "sku": "SKU-001"}
            }
        }
        mock_async_client.post.side_effect = [mock_response, mock_detalles_response]
        
        registros, total = await service.listar_registros_paginados(
            skip=0, limit=10, categoria="MEDICAMENTOS"
        )
        
        assert total == 1
        assert len(registros) == 1

    @patch("services.inventario_service.httpx.AsyncClient")
    async def test_listar_registros_paginados_estado_filter(self, mock_http_client: Mock, service: InventarioService, mock_db: Mock):
        """Test: Listar registros filtrados por estado"""
        prod_id_1 = uuid4()
        
        # Mock inventario record
        mock_registro = Mock(spec=Inventario)
        mock_registro.producto_id = prod_id_1
        mock_registro.to_dict.return_value = {
            "producto_id": str(prod_id_1),
            "lote": "L1",
            "estado": "DISPONIBLE"
        }
        
        # Mock DB query chain
        mock_query = Mock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.count.return_value = 1
        mock_query.order_by.return_value.offset.return_value.limit.return_value.all.return_value = [mock_registro]
        
        # Mock detalles productos
        mock_async_client = mock_http_client.return_value.__aenter__.return_value
        mock_detalles_response = Mock(status_code=200)
        mock_detalles_response.json.return_value = {
            "detalles": {
                str(prod_id_1): {"nombre": "Producto Test", "sku": "SKU-001"}
            }
        }
        mock_async_client.post.return_value = mock_detalles_response
        
        registros, total = await service.listar_registros_paginados(
            skip=0, limit=10, estado="DISPONIBLE"
        )
        
        assert total == 1
        assert len(registros) == 1
        # Verify estado filter was applied
        mock_query.filter.assert_called()

    @patch("services.inventario_service.httpx.AsyncClient")
    async def test_listar_registros_paginados_text_search_no_productos_found(self, mock_http_client: Mock, service: InventarioService, mock_db: Mock):
        """Test: Retornar vacío cuando text_search no encuentra productos y no hay ubicacion match"""
        # Mock productos service response (no matches) - this is for filter-ids endpoint
        mock_async_client = mock_http_client.return_value.__aenter__.return_value
        mock_filter_response = Mock(status_code=200)
        mock_filter_response.json.return_value = {
            "producto_ids": []
        }
        # When text_search is provided but no productos found, it still filters by ubicacion
        # So we need to mock the filter-ids call, but the query will still run with ubicacion filter
        mock_async_client.post.return_value = mock_filter_response
        
        # Mock DB query chain - no ubicacion matches either
        mock_query = Mock()
        mock_db.query.return_value = mock_query
        # filter() is called with or_() when text_search is provided
        mock_query.filter.return_value = mock_query
        mock_query.count.return_value = 0
        # Mock the full query chain for order_by, offset, limit, all
        mock_query.order_by.return_value.offset.return_value.limit.return_value.all.return_value = []
        
        registros, total = await service.listar_registros_paginados(
            skip=0, limit=10, text_search="Inexistente"
        )
        
        assert total == 0
        assert len(registros) == 0