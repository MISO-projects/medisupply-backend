# src/visitas/tests/test_visita_service.py

import pytest
from unittest.mock import Mock, patch, AsyncMock
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError 
from datetime import date, datetime
from uuid import uuid4
import httpx
from http import HTTPStatus

from services.visita_service import VisitaService
from db.visita import Visita
from schemas.visita_schema import CrearRutaVisitaSchema, ActualizarVisitaSchema
from fastapi import HTTPException

pytestmark = pytest.mark.asyncio

class TestVisitaService:

    @pytest.fixture
    def mock_db(self):
        """Fixture de un mock de la sesión de BBDD"""
        return Mock(spec=Session)

    @pytest.fixture
    def service(self, mock_db: Mock):
        """
        Fixture del servicio. Parcheamos 'get_redis_client' 
        que es llamado DENTRO del __init__.
        """
        with patch('services.visita_service.get_redis_client') as mock_get_redis:
            mock_redis = Mock()
            mock_get_redis.return_value = mock_redis
            service_instance = VisitaService(db=mock_db)
            yield service_instance

    @patch("services.visita_service.httpx.AsyncClient")
    async def test_get_cliente_data_success(self, mock_http_client: Mock, service: VisitaService):
        """Test: _get_cliente_data exitoso"""
        cliente_id = str(uuid4())
        mock_cliente_data = [{"id": cliente_id, "id_vendedor": str(uuid4())}]

        mock_async_client = mock_http_client.return_value.__aenter__.return_value
        mock_response = Mock(status_code=HTTPStatus.OK)
        mock_response.json.return_value = mock_cliente_data
        mock_async_client.post.return_value = mock_response

        data = await service._get_cliente_data(cliente_id)
        
        assert data == mock_cliente_data[0]
        mock_async_client.post.assert_called_once()

    @patch("services.visita_service.httpx.AsyncClient")
    async def test_get_cliente_data_not_found(self, mock_http_client: Mock, service: VisitaService):
        """Test: _get_cliente_data falla si el cliente no existe"""
        cliente_id = str(uuid4())
        
        mock_async_client = mock_http_client.return_value.__aenter__.return_value
        mock_response = Mock(status_code=HTTPStatus.OK)
        mock_response.json.return_value = [] 
        mock_async_client.post.return_value = mock_response

        with pytest.raises(HTTPException) as e:
            await service._get_cliente_data(cliente_id)
        assert e.value.status_code == HTTPStatus.NOT_FOUND

    @patch("services.visita_service.httpx.AsyncClient")
    async def test_crear_ruta_visita_success(self, mock_http_client: Mock, service: VisitaService, mock_db: Mock):
        """Test: Crear una ruta de visita exitosamente"""
        cliente_id = uuid4()
        vendedor_id = uuid4()
        data = CrearRutaVisitaSchema(cliente_id=cliente_id)
        
        mock_cliente_data = [{"id": str(cliente_id), "id_vendedor": str(vendedor_id)}]
        mock_async_client = mock_http_client.return_value.__aenter__.return_value
        mock_response = Mock(status_code=HTTPStatus.OK)
        mock_response.json.return_value = mock_cliente_data
        mock_async_client.post.return_value = mock_response

        mock_visita = Mock(spec=Visita)
        mock_visita.to_dict.return_value = {"id": str(uuid4()), "cliente_id": cliente_id}
        mock_db.refresh.side_effect = lambda x: setattr(x, 'to_dict', mock_visita.to_dict)

        resultado = await service.crear_ruta_visita(data)
        
        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()
        assert resultado["cliente_id"] == cliente_id

    @patch("services.visita_service.httpx.AsyncClient")
    async def test_crear_ruta_visita_sin_vendedor(self, mock_http_client: Mock, service: VisitaService):
        """Test: Falla si el cliente no tiene vendedor asignado"""
        cliente_id = uuid4()
        data = CrearRutaVisitaSchema(cliente_id=cliente_id)
        
        mock_cliente_data = [{"id": str(cliente_id), "id_vendedor": None}] # Sin vendedor
        mock_async_client = mock_http_client.return_value.__aenter__.return_value
        mock_response = Mock(status_code=HTTPStatus.OK)
        mock_response.json.return_value = mock_cliente_data
        mock_async_client.post.return_value = mock_response

        with pytest.raises(HTTPException) as e:
            await service.crear_ruta_visita(data)
        assert e.value.status_code == HTTPStatus.BAD_REQUEST
        assert "no tiene un vendedor asignado" in e.value.detail


    @patch("services.visita_service.httpx.AsyncClient")
    async def test_get_rutas_por_fecha_y_vendedor_success(self, mock_http_client: Mock, service: VisitaService, mock_db: Mock):
        """Test: Obtener rutas del día exitosamente"""
        test_fecha = date(2025, 1, 1)
        test_vendedor_id = uuid4()
        cliente_id_1 = uuid4()
        
        fecha_programada = datetime(2025, 1, 1, 9, 30)
        
        mock_visita_db = Visita(
            cliente_id=cliente_id_1,
            vendedor_id=test_vendedor_id,
            fecha_visita_programada=fecha_programada
        )
        mock_visita_db.id = uuid4()
        mock_visita_db.estado = "PENDIENTE"
        
        mock_db.query.return_value.filter.return_value.order_by.return_value.all.return_value = [mock_visita_db]

        mock_cliente_data = [{
            "id": str(cliente_id_1), 
            "nombre": "Cliente Test",
            "address": "Calle Falsa 123"
        }]
        mock_async_client = mock_http_client.return_value.__aenter__.return_value
        mock_response = Mock(status_code=HTTPStatus.OK)
        mock_response.json.return_value = mock_cliente_data
        mock_async_client.post.return_value = mock_response

        resultados = await service.get_rutas_por_fecha_y_vendedor(test_fecha, test_vendedor_id)

        assert len(resultados) == 1
        assert resultados[0].nombre == "Cliente Test"
        assert resultados[0].hora_de_la_cita == "09:30"

    async def test_actualizar_visita_not_found(self, service: VisitaService, mock_db: Mock):
        """Test: Actualizar visita falla si no se encuentra"""
        visita_id = uuid4()
        data = ActualizarVisitaSchema(estado="REALIZADA")
        
        mock_db.query.return_value.filter.return_value.first.return_value = None

        with pytest.raises(HTTPException) as e:
            await service.actualizar_visita(visita_id, data)
        assert e.value.status_code == HTTPStatus.NOT_FOUND

    async def test_actualizar_visita_transicion_invalida(self, service: VisitaService, mock_db: Mock):
        """Test: Falla al intentar cambiar estado de visita 'REALIZADA'"""
        visita_id = uuid4()
        data = ActualizarVisitaSchema(estado="PENDIENTE") # Intentar regresar a PENDIENTE

        dummy_cliente_id = uuid4()
        dummy_vendedor_id = uuid4()
        dummy_fecha = datetime.now()

        mock_visita_db = Visita(
            cliente_id=dummy_cliente_id,
            vendedor_id=dummy_vendedor_id,
            fecha_visita_programada=dummy_fecha
        )
        mock_visita_db.id = visita_id
        mock_visita_db.estado = "REALIZADA" # Asigna el estado actual
        
        mock_db.query.return_value.filter.return_value.first.return_value = mock_visita_db
        
        with pytest.raises(HTTPException) as e:
            await service.actualizar_visita(visita_id, data)
        assert e.value.status_code == HTTPStatus.BAD_REQUEST
        assert "No se puede cambiar el estado" in e.value.detail
        

    @patch("services.visita_service.httpx.AsyncClient")
    async def test_get_cliente_data_request_error(self, mock_http_client: Mock, service: VisitaService):
        """Test: _get_cliente_data falla si httpx lanza RequestError"""
        cliente_id = str(uuid4())
        
        mock_async_client = mock_http_client.return_value.__aenter__.return_value
        mock_async_client.post.side_effect = httpx.RequestError("Error de red simulado")

        with pytest.raises(HTTPException) as e:
            await service._get_cliente_data(cliente_id)
        assert e.value.status_code == HTTPStatus.SERVICE_UNAVAILABLE
        assert "No se pudo conectar" in e.value.detail

    @patch("services.visita_service.httpx.AsyncClient")
    async def test_crear_ruta_visita_vendedor_id_invalido(self, mock_http_client: Mock, service: VisitaService):
        """Test: Falla 500 si el id_vendedor recibido del cliente no es un UUID"""
        cliente_id = uuid4()
        data = CrearRutaVisitaSchema(cliente_id=cliente_id)
        
        mock_cliente_data = [{"id": str(cliente_id), "id_vendedor": "no-es-un-uuid"}]
        
        mock_async_client = mock_http_client.return_value.__aenter__.return_value
        mock_response = Mock(status_code=HTTPStatus.OK)
        mock_response.json.return_value = mock_cliente_data
        mock_async_client.post.return_value = mock_response

        with pytest.raises(HTTPException) as e:
            await service.crear_ruta_visita(data)
        assert e.value.status_code == HTTPStatus.INTERNAL_SERVER_ERROR
        assert "ID del vendedor recibido" in e.value.detail

    @patch("services.visita_service.httpx.AsyncClient")
    async def test_crear_ruta_visita_db_integrity_error(self, mock_http_client: Mock, service: VisitaService, mock_db: Mock):
        """Test: Falla 409 si la BBDD lanza un IntegrityError"""
        cliente_id = uuid4()
        vendedor_id = uuid4()
        data = CrearRutaVisitaSchema(cliente_id=cliente_id)
        
        mock_cliente_data = [{"id": str(cliente_id), "id_vendedor": str(vendedor_id)}]
        mock_async_client = mock_http_client.return_value.__aenter__.return_value
        mock_response = Mock(status_code=HTTPStatus.OK)
        mock_response.json.return_value = mock_cliente_data
        mock_async_client.post.return_value = mock_response

        mock_db.commit.side_effect = IntegrityError("Simulación de error", "params", "orig")
        
        with pytest.raises(HTTPException) as e:
            await service.crear_ruta_visita(data)
        assert e.value.status_code == HTTPStatus.CONFLICT
        mock_db.rollback.assert_called_once()


    @patch("services.visita_service.httpx.AsyncClient")
    async def test_get_rutas_por_fecha_y_vendedor_sin_visitas(self, mock_http_client: Mock, service: VisitaService, mock_db: Mock):
        """Test: Devuelve lista vacía si no se encuentran visitas en la BBDD"""
        test_fecha = date(2025, 1, 1)
        test_vendedor_id = uuid4()
        
        mock_db.query.return_value.filter.return_value.order_by.return_value.all.return_value = []

        resultados = await service.get_rutas_por_fecha_y_vendedor(test_fecha, test_vendedor_id)

        assert resultados == []
        mock_http_client.assert_not_called()

    async def test_get_visita_detalle_por_id_not_found(self, service: VisitaService, mock_db: Mock):
        """Test: get_visita_detalle_por_id falla 404 si no se encuentra"""
        visita_id = uuid4()
        mock_db.query.return_value.filter.return_value.first.return_value = None

        with pytest.raises(HTTPException) as e:
            await service.get_visita_detalle_por_id(visita_id)
        assert e.value.status_code == HTTPStatus.NOT_FOUND

    @patch("services.visita_service.httpx.AsyncClient")
    async def test_get_visita_detalle_cliente_service_falla(self, mock_http_client: Mock, service: VisitaService, mock_db: Mock):
        """Test: get_visita_detalle_por_id devuelve datos por defecto si el servicio de cliente falla"""
        visita_id = uuid4()
        cliente_id = uuid4()

        # 1. Mockear BBDD (la visita SÍ existe)
        dummy_vendedor_id = uuid4()
        dummy_fecha = datetime.now()
        mock_visita_db = Visita(
            cliente_id=cliente_id,
            vendedor_id=dummy_vendedor_id,
            fecha_visita_programada=dummy_fecha
        )
        mock_visita_db.id = visita_id
        mock_visita_db.estado = "PENDIENTE"
        mock_visita_db.to_dict = lambda: {
            "id": visita_id, "cliente_id": cliente_id, "vendedor_id": dummy_vendedor_id,
            "fecha_visita_programada": dummy_fecha, "estado": "PENDIENTE",
            "created_at": dummy_fecha, "updated_at": None, "cliente_contacto": None,
            "detalle": None, "evidencia": None, "inicio": None, "fin": None
        }
        mock_db.query.return_value.filter.return_value.first.return_value = mock_visita_db

        mock_async_client = mock_http_client.return_value.__aenter__.return_value
        mock_async_client.post.side_effect = httpx.RequestError("Error de red simulado")
        
        resultado = await service.get_visita_detalle_por_id(visita_id)
        
        assert resultado.id == visita_id
        assert resultado.nombre_institucion == "Cliente no disponible"
        assert resultado.direccion == "Dirección no disponible"

    async def test_actualizar_visita_payload_vacio(self, service: VisitaService, mock_db: Mock):
        """Test: Falla 400 si se intenta actualizar sin datos"""
        visita_id = uuid4()
        data = ActualizarVisitaSchema() 

        dummy_cliente_id = uuid4()
        dummy_vendedor_id = uuid4()
        dummy_fecha = datetime.now()
        mock_visita_db = Visita(
            cliente_id=dummy_cliente_id,
            vendedor_id=dummy_vendedor_id,
            fecha_visita_programada=dummy_fecha
        )
        mock_visita_db.id = visita_id
        mock_db.query.return_value.filter.return_value.first.return_value = mock_visita_db

        with pytest.raises(HTTPException) as e:
            await service.actualizar_visita(visita_id, data)
        assert e.value.status_code == HTTPStatus.BAD_REQUEST
        assert "No se proporcionaron datos" in e.value.detail