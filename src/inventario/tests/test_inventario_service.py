# src/inventario/tests/test_inventario_service.py

import pytest
from unittest.mock import Mock, patch, AsyncMock, call
from sqlalchemy.orm import Session
from datetime import date, timedelta
from uuid import uuid4
import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), '../..'))
from auditoria.db.models import AuditLog

from services.inventario_service import InventarioService
from db.inventario_model import Inventario
from schemas.inventario_schema import CrearRegistroInventarioSchema, ActualizarInventarioSchema
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
        """Test: Crear un registro de inventario exitosamente con auditoría"""
        data = CrearRegistroInventarioSchema(
            producto_id=uuid4(),
            lote="LOTE-123",
            fecha_vencimiento=date.today() + timedelta(days=30),
            cantidad=100
        )
        usuario_id = str(uuid4())
        ip_origen = "192.168.1.1"
    
        mock_inventario = Mock(spec=Inventario)
        mock_inventario.id = uuid4()
        mock_inventario.producto_id = data.producto_id
        mock_inventario.lote = "LOTE-123"
        mock_inventario.cantidad = 100
        mock_inventario.fecha_vencimiento = data.fecha_vencimiento
        mock_inventario.to_dict.return_value = {"id": str(mock_inventario.id), "lote": "LOTE-123"}
        mock_db.refresh.side_effect = lambda x: setattr(x, 'to_dict', mock_inventario.to_dict)
    
        resultado = await service.crear_registro_inventario(
            data, 
            usuario_id=usuario_id, 
            ip_origen=ip_origen
        )
    
        # Verificar que se llamó add() dos veces: inventario + audit_log
        assert mock_db.add.call_count == 2
        
        # Verificar que el segundo add() es para AuditLog
        second_call_arg = mock_db.add.call_args_list[1][0][0]
        assert isinstance(second_call_arg, AuditLog)
        assert second_call_arg.operation == "CREAR"
        assert second_call_arg.event_type == "inventory_operation"
        
        mock_db.flush.assert_called_once()
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

    @pytest.mark.asyncio
    async def test_actualizar_registro_inventario_success(self, service: InventarioService, mock_db: Mock):
        """Test: Actualizar un registro de inventario exitosamente con auditoría"""
        inventario_id = str(uuid4())
        usuario_id = str(uuid4())
        ip_origen = "192.168.1.1"
        
        # Mock del registro existente
        mock_inventario = Mock(spec=Inventario)
        mock_inventario.id = uuid4()
        mock_inventario.producto_id = uuid4()
        mock_inventario.lote = "LOTE-VIEJO"
        mock_inventario.cantidad = 50
        mock_inventario.ubicacion = "BODEGA-A"
        mock_inventario.estado = "DISPONIBLE"
        mock_inventario.temperatura_requerida = "AMBIENTE"
        mock_inventario.fecha_vencimiento = date.today() + timedelta(days=30)
        mock_inventario.condiciones_especiales = None
        mock_inventario.observaciones = None
        mock_inventario.to_dict.return_value = {
            "id": str(mock_inventario.id),
            "lote": "LOTE-NUEVO",
            "cantidad": 75
        }
        
        # Mock query
        mock_query = Mock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value.first.return_value = mock_inventario
        
        # Datos de actualización
        from schemas.inventario_schema import ActualizarInventarioSchema
        datos_actualizacion = ActualizarInventarioSchema(
            lote="LOTE-NUEVO",
            cantidad=75
        )
        
        resultado = await service.actualizar_registro_inventario(
            inventario_id=inventario_id,
            datos_actualizacion=datos_actualizacion,
            usuario_id=usuario_id,
            ip_origen=ip_origen
        )
        
        # Verificar que se agregó el AuditLog
        assert mock_db.add.call_count == 1
        audit_log_arg = mock_db.add.call_args[0][0]
        assert isinstance(audit_log_arg, AuditLog)
        assert audit_log_arg.operation == "MODIFICAR"
        assert audit_log_arg.event_type == "inventory_operation"
        assert "lote" in audit_log_arg.cambios
        assert "cantidad" in audit_log_arg.cambios
        
        # Verificar cambios registrados
        assert audit_log_arg.cambios["lote"]["anterior"] == "LOTE-VIEJO"
        assert audit_log_arg.cambios["lote"]["nuevo"] == "LOTE-NUEVO"
        assert audit_log_arg.cambios["cantidad"]["anterior"] == 50
        assert audit_log_arg.cambios["cantidad"]["nuevo"] == 75
        
        mock_db.commit.assert_called_once()
        mock_db.refresh.assert_called_once()
        assert resultado["lote"] == "LOTE-NUEVO"

    @pytest.mark.asyncio
    async def test_actualizar_registro_inventario_not_found(self, service: InventarioService, mock_db: Mock):
        """Test: Fallar al actualizar un registro que no existe"""
        inventario_id = str(uuid4())
        usuario_id = str(uuid4())
        
        # Mock query que retorna None (no encontrado)
        mock_query = Mock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value.first.return_value = None
        
        from schemas.inventario_schema import ActualizarInventarioSchema
        datos_actualizacion = ActualizarInventarioSchema(cantidad=100)
        
        with pytest.raises(HTTPException) as exc_info:
            await service.actualizar_registro_inventario(
                inventario_id=inventario_id,
                datos_actualizacion=datos_actualizacion,
                usuario_id=usuario_id,
                ip_origen="192.168.1.1"
            )
        
        assert exc_info.value.status_code == 404
        assert "no encontrado" in exc_info.value.detail.lower()

    @pytest.mark.asyncio
    async def test_eliminar_registro_inventario_success(self, service: InventarioService, mock_db: Mock):
        """Test: Eliminar un registro de inventario exitosamente con auditoría"""
        inventario_id = str(uuid4())
        usuario_id = str(uuid4())
        ip_origen = "192.168.1.1"
        
        # Mock del registro existente
        mock_inventario = Mock(spec=Inventario)
        mock_inventario.id = uuid4()
        mock_inventario.producto_id = uuid4()
        mock_inventario.lote = "LOTE-123"
        mock_inventario.cantidad = 50
        mock_inventario.ubicacion = "BODEGA-A"
        mock_inventario.estado = "DISPONIBLE"
        mock_inventario.temperatura_requerida = "AMBIENTE"
        mock_inventario.fecha_vencimiento = date.today() + timedelta(days=30)
        mock_inventario.condiciones_especiales = None
        mock_inventario.observaciones = None
        mock_inventario.fecha_recepcion = date.today()
        mock_inventario.created_at = date.today()
        mock_inventario.updated_at = None
        
        # Mock query
        mock_query = Mock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value.first.return_value = mock_inventario
        
        resultado = await service.eliminar_registro_inventario(
            inventario_id=inventario_id,
            usuario_id=usuario_id,
            ip_origen=ip_origen
        )
        
        # Verificar que se agregó el AuditLog
        assert mock_db.add.call_count == 1
        audit_log_arg = mock_db.add.call_args[0][0]
        assert isinstance(audit_log_arg, AuditLog)
        assert audit_log_arg.operation == "ELIMINAR"
        assert audit_log_arg.event_type == "inventory_operation"
        
        # Verificar que se guardaron todos los datos en datos_operacion
        assert "lote" in audit_log_arg.datos_operacion
        assert audit_log_arg.datos_operacion["lote"] == "LOTE-123"
        assert audit_log_arg.datos_operacion["cantidad"] == 50
        
        # Verificar que se llamó delete
        mock_db.delete.assert_called_once_with(mock_inventario)
        mock_db.commit.assert_called_once()
        assert "eliminado correctamente" in resultado["message"]

    @pytest.mark.asyncio
    async def test_eliminar_registro_inventario_not_found(self, service: InventarioService, mock_db: Mock):
        """Test: Fallar al eliminar un registro que no existe"""
        inventario_id = str(uuid4())
        usuario_id = str(uuid4())
        
        # Mock query que retorna None (no encontrado)
        mock_query = Mock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value.first.return_value = None
        
        with pytest.raises(HTTPException) as exc_info:
            await service.eliminar_registro_inventario(
                inventario_id=inventario_id,
                usuario_id=usuario_id,
                ip_origen="192.168.1.1"
            )
        
        assert exc_info.value.status_code == 404
        assert "no encontrado" in exc_info.value.detail.lower()

    @pytest.mark.asyncio
    async def test_crear_registro_rollback_on_error(self, service: InventarioService, mock_db: Mock):
        """Test: Verificar rollback si falla la creación (atomicidad)"""
        data = CrearRegistroInventarioSchema(
            producto_id=uuid4(),
            lote="LOTE-123",
            fecha_vencimiento=date.today() + timedelta(days=30),
            cantidad=100
        )
        
        # Simular error en commit
        mock_db.commit.side_effect = Exception("Error de base de datos")
        
        with pytest.raises(HTTPException):
            await service.crear_registro_inventario(data, usuario_id=str(uuid4()))
        
        # Verificar que se llamó rollback
        mock_db.rollback.assert_called()

    @pytest.mark.asyncio
    async def test_actualizar_registro_rollback_on_error(self, service: InventarioService, mock_db: Mock):
        """Test: Verificar rollback si falla la actualización (atomicidad)"""
        inventario_id = str(uuid4())
        
        # Mock del registro existente
        mock_inventario = Mock(spec=Inventario)
        mock_inventario.id = uuid4()
        mock_inventario.producto_id = uuid4()
        mock_inventario.lote = "LOTE-VIEJO"
        mock_inventario.cantidad = 50
        mock_inventario.ubicacion = "BODEGA-A"
        mock_inventario.estado = "DISPONIBLE"
        mock_inventario.temperatura_requerida = "AMBIENTE"
        mock_inventario.fecha_vencimiento = date.today()
        mock_inventario.condiciones_especiales = None
        mock_inventario.observaciones = None
        
        mock_query = Mock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value.first.return_value = mock_inventario
        
        # Simular error en commit
        mock_db.commit.side_effect = Exception("Error de base de datos")
        
        from schemas.inventario_schema import ActualizarInventarioSchema
        datos = ActualizarInventarioSchema(cantidad=100)
        
        with pytest.raises(HTTPException):
            await service.actualizar_registro_inventario(
                inventario_id=str(inventario_id),
                datos_actualizacion=datos,
                usuario_id=str(uuid4())
            )
        
        # Verificar que se llamó rollback
        mock_db.rollback.assert_called()

    @pytest.mark.asyncio
    async def test_eliminar_registro_rollback_on_error(self, service: InventarioService, mock_db: Mock):
        """Test: Verificar rollback si falla la eliminación (atomicidad)"""
        inventario_id = str(uuid4())
        
        # Mock del registro existente
        mock_inventario = Mock(spec=Inventario)
        mock_inventario.id = uuid4()
        mock_inventario.producto_id = uuid4()
        mock_inventario.lote = "LOTE-123"
        mock_inventario.cantidad = 50
        mock_inventario.ubicacion = "BODEGA-A"
        mock_inventario.estado = "DISPONIBLE"
        mock_inventario.temperatura_requerida = "AMBIENTE"
        mock_inventario.fecha_vencimiento = date.today()
        mock_inventario.condiciones_especiales = None
        mock_inventario.observaciones = None
        mock_inventario.fecha_recepcion = date.today()
        mock_inventario.created_at = date.today()
        mock_inventario.updated_at = None
        
        mock_query = Mock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value.first.return_value = mock_inventario
        
        # Simular error en commit
        mock_db.commit.side_effect = Exception("Error de base de datos")
        
        with pytest.raises(HTTPException):
            await service.eliminar_registro_inventario(
                inventario_id=str(inventario_id),
                usuario_id=str(uuid4())
            )
        
        # Verificar que se llamó rollback
        mock_db.rollback.assert_called()