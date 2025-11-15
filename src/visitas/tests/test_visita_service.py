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
from schemas.visita_schema import (
    CrearRutaVisitaSchema, 
    ActualizarVisitaSchema, 
    VisitaDetalleResponseSchema
)
from fastapi import HTTPException

pytestmark = pytest.mark.asyncio

def create_mock_visita(visita_id: uuid4, cliente_id, vendedor_id, estado="PENDIENTE"):
    """
    Crea un objeto Visita mockeado.
    AHORA ACEPTA visita_id COMO ARGUMENTO.
    """
    fecha = datetime.now()
    mock_visita = Visita(
        cliente_id=cliente_id,
        vendedor_id=vendedor_id,
        fecha_visita_programada=fecha
    )
    mock_visita.id = visita_id 
    mock_visita.estado = estado
    mock_visita.to_dict = lambda: {
        "id": visita_id, 
        "cliente_id": cliente_id, "vendedor_id": vendedor_id,
        "fecha_visita_programada": fecha, "estado": estado, "created_at": fecha, 
        "updated_at": None, "cliente_contacto": None, "detalle": None, 
        "evidencia": None, "inicio": None, "fin": None
    }
    return mock_visita

def mock_db_query_side_effect(pendientes_list, otras_list):
    """Crea un side_effect para simular las dos consultas de get_rutas"""
    def query_side_effect(*args): 
        mock_filter = Mock()
        mock_filter.all.return_value = pendientes_list
        mock_filter.order_by.return_value.all.return_value = otras_list
        return mock_filter
    return query_side_effect

def mock_http_responses(mock_async_client, post_response=None, get_responses=None):
    """Configura las respuestas mock para httpx.AsyncClient"""
    if post_response:
        mock_async_client.post.return_value = post_response
    
    if get_responses:
        mock_async_client.get.side_effect = get_responses

# ---------------------------------

class TestVisitaService:

    @pytest.fixture
    def mock_db(self):
        """Fixture de un mock de la sesión de BBDD"""
        return Mock(spec=Session)

    @pytest.fixture
    def service(self, mock_db: Mock):
        """
        Fixture del servicio. Parcheamos 'get_redis_client' 
        y seteamos la API key.
        """
        with patch('services.visita_service.get_redis_client') as mock_get_redis:
            mock_redis = Mock()
            mock_get_redis.return_value = mock_redis
            service_instance = VisitaService(db=mock_db)
            service_instance.google_maps_api_key = "fake-key-para-tests"
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
        mock_db.refresh.side_effect = lambda x: setattr(x, 'to_dict', lambda: {"id": str(uuid4()), "cliente_id": cliente_id})

        resultado = await service.crear_ruta_visita(data)
        
        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()
        assert resultado["cliente_id"] == cliente_id

    @patch("services.visita_service.httpx.AsyncClient")
    async def test_crear_ruta_visita_sin_vendedor(self, mock_http_client: Mock, service: VisitaService):
        """Test: Falla si el cliente no tiene vendedor asignado"""
        cliente_id = uuid4()
        data = CrearRutaVisitaSchema(cliente_id=cliente_id)
        mock_cliente_data = [{"id": str(cliente_id), "id_vendedor": None}]
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
        """Test: Obtener rutas del día exitosamente (optimizadas)"""
        test_fecha = date(2025, 1, 1)
        test_vendedor_id = uuid4()
        cliente_id_1 = uuid4()
        mock_visita_db = create_mock_visita(uuid4(), cliente_id_1, test_vendedor_id, "PENDIENTE")
        
        # Mock de BD: 1 pendiente, 0 otras
        mock_db.query.return_value.filter.side_effect = mock_db_query_side_effect(
            pendientes_list=[mock_visita_db],
            otras_list=[]
        )

        mock_cliente_data = [{"id": str(cliente_id_1), "nombre": "Cliente Test", "address": "7.1,-73.1,Calle Falsa 123"}]
        mock_async_client = mock_http_client.return_value.__aenter__.return_value
        
        mock_response_clientes = Mock(status_code=HTTPStatus.OK)
        mock_response_clientes.json.return_value = mock_cliente_data
        
        mock_gmaps_response = Mock(status_code=HTTPStatus.OK)
        mock_gmaps_response.json.return_value = {
            "status": "OK",
            "routes": [{"waypoint_order": [0], "legs": [{"duration": {"text": "15 min"}}]}]
        }
        mock_async_client.post.return_value = mock_response_clientes
        mock_async_client.get.return_value = mock_gmaps_response

        resultados = await service.get_rutas_por_fecha_y_vendedor(test_fecha, test_vendedor_id, 7.0, -73.0)

        assert len(resultados) == 1
        assert resultados[0].nombre == "Cliente Test"
        assert resultados[0].hora_de_la_cita == "15 min"

    @patch("services.visita_service.httpx.AsyncClient")
    async def test_get_rutas_google_maps_falla(self, mock_http_client: Mock, service: VisitaService, mock_db: Mock):
        """Test: Devuelve ruta sin optimizar si Google Maps falla"""
        test_fecha = date(2025, 1, 1)
        test_vendedor_id = uuid4()
        cliente_id_1 = uuid4()
        mock_visita_db = create_mock_visita(uuid4(), cliente_id_1, test_vendedor_id, "PENDIENTE")

        mock_db.query.return_value.filter.side_effect = mock_db_query_side_effect([mock_visita_db], [])
        
        mock_cliente_data = [{"id": str(cliente_id_1), "nombre": "Cliente Test", "address": "7.1,-73.1,Calle Falsa 123"}]
        mock_async_client = mock_http_client.return_value.__aenter__.return_value
        
        mock_response_clientes = Mock(status_code=HTTPStatus.OK)
        mock_response_clientes.json.return_value = mock_cliente_data
        mock_async_client.post.return_value = mock_response_clientes

        mock_gmaps_response = Mock(status_code=HTTPStatus.OK)
        mock_gmaps_response.json.return_value = {"status": "REQUEST_DENIED"}
        mock_async_client.get.return_value = mock_gmaps_response

        resultados = await service.get_rutas_por_fecha_y_vendedor(test_fecha, test_vendedor_id, 7.0, -73.0)
        
        assert len(resultados) == 1
        assert resultados[0].hora_de_la_cita == "Sin calcular"

    @patch("services.visita_service.httpx.AsyncClient")
    async def test_get_rutas_visitas_sin_coordenadas(self, mock_http_client: Mock, service: VisitaService, mock_db: Mock):
        """Test: Devuelve ruta sin optimizar si las visitas no tienen coordenadas (NA,NA)"""
        test_fecha = date(2025, 1, 1)
        test_vendedor_id = uuid4()
        cliente_id_1 = uuid4()
        mock_visita_db = create_mock_visita(uuid4(), cliente_id_1, test_vendedor_id, "PENDIENTE")

        mock_db.query.return_value.filter.side_effect = mock_db_query_side_effect([mock_visita_db], [])
        
        mock_cliente_data = [{"id": str(cliente_id_1), "nombre": "Cliente Test", "address": "NA,NA,Calle Falsa 123"}]
        mock_async_client = mock_http_client.return_value.__aenter__.return_value
        
        mock_response_clientes = Mock(status_code=HTTPStatus.OK)
        mock_response_clientes.json.return_value = mock_cliente_data
        mock_async_client.post.return_value = mock_response_clientes

        resultados = await service.get_rutas_por_fecha_y_vendedor(test_fecha, test_vendedor_id, 7.0, -73.0)
        
        mock_async_client.get.assert_not_called()
        assert len(resultados) == 1
        assert resultados[0].hora_de_la_cita == "Sin calcular"

    async def test_actualizar_visita_not_found(self, service: VisitaService, mock_db: Mock):
        visita_id = uuid4()
        data = ActualizarVisitaSchema(estado="REALIZADA")
        mock_db.query.return_value.filter.return_value.first.return_value = None
        with pytest.raises(HTTPException) as e:
            await service.actualizar_visita(visita_id, data)
        assert e.value.status_code == HTTPStatus.NOT_FOUND

    @patch("services.visita_service.VisitaService._get_cliente_data", new_callable=AsyncMock)
    @patch("services.visita_service.VisitaService._get_top_products_data", new_callable=AsyncMock)
    @patch("services.visita_service.VisitaService._get_user_contact_for_client", new_callable=AsyncMock)
    @patch("services.visita_service.VisitaService._get_single_route_travel_time", new_callable=AsyncMock)
    async def test_actualizar_visita_transicion_invalida(
        self, mock_get_time: Mock, mock_get_contact: Mock, mock_get_products: Mock, mock_get_cliente: Mock, 
        service: VisitaService, mock_db: Mock
    ):
        """Test: Falla al intentar cambiar estado de visita 'REALIZADA'"""
        visita_id = uuid4()
        data = ActualizarVisitaSchema(estado="PENDIENTE")
        mock_visita_db = create_mock_visita(visita_id, uuid4(), uuid4(), "REALIZADA")
        
        mock_db.query.return_value.filter.return_value.first.return_value = mock_visita_db
        
        with pytest.raises(HTTPException) as e:
            await service.actualizar_visita(visita_id, data)
        assert e.value.status_code == HTTPStatus.BAD_REQUEST
        assert "No se puede cambiar el estado" in e.value.detail
        

    @patch("services.visita_service.httpx.AsyncClient")
    async def test_get_cliente_data_request_error(self, mock_http_client: Mock, service: VisitaService):
        cliente_id = str(uuid4())
        mock_async_client = mock_http_client.return_value.__aenter__.return_value
        mock_async_client.post.side_effect = httpx.RequestError("Error de red simulado")
        with pytest.raises(HTTPException) as e:
            await service._get_cliente_data(cliente_id)
        assert e.value.status_code == HTTPStatus.SERVICE_UNAVAILABLE

    @patch("services.visita_service.httpx.AsyncClient")
    async def test_crear_ruta_visita_vendedor_id_invalido(self, mock_http_client: Mock, service: VisitaService):
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

    @patch("services.visita_service.httpx.AsyncClient")
    async def test_crear_ruta_visita_db_integrity_error(self, mock_http_client: Mock, service: VisitaService, mock_db: Mock):
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
        
        mock_db.query.return_value.filter.side_effect = mock_db_query_side_effect(
            pendientes_list=[],
            otras_list=[]
        )

        resultados = await service.get_rutas_por_fecha_y_vendedor(test_fecha, test_vendedor_id)

        assert resultados == []
        mock_http_client.assert_not_called()

    async def test_get_visita_detalle_por_id_not_found(self, service: VisitaService, mock_db: Mock):
        visita_id = uuid4()
        mock_db.query.return_value.filter.return_value.first.return_value = None
        with pytest.raises(HTTPException) as e:
            await service.get_visita_detalle_por_id(visita_id)
        assert e.value.status_code == HTTPStatus.NOT_FOUND

    @patch("services.visita_service.httpx.AsyncClient")
    async def test_get_visita_detalle_cliente_service_falla(self, mock_http_client: Mock, service: VisitaService, mock_db: Mock):
        """Test: get_visita_detalle_por_id devuelve datos por defecto si servicios externos fallan"""
        visita_id = uuid4()
        cliente_id = uuid4()

        mock_visita_db = create_mock_visita(visita_id, cliente_id, uuid4(), "PENDIENTE")
        mock_db.query.return_value.filter.return_value.first.return_value = mock_visita_db
        
        mock_db.query.return_value.filter.return_value.order_by.return_value.limit.return_value.all.return_value = []

        mock_async_client = mock_http_client.return_value.__aenter__.return_value
        mock_async_client.post.side_effect = httpx.RequestError("Error de red simulado")
        
        mock_response_ok_empty = Mock(status_code=HTTPStatus.OK)
        mock_response_ok_empty.json.return_value = {"data": []} 
        mock_response_notfound = Mock(status_code=HTTPStatus.NOT_FOUND) 
        
        mock_async_client.get.side_effect = [
            mock_response_ok_empty, 
            mock_response_notfound, 
        ]
    
        resultado = await service.get_visita_detalle_por_id(visita_id)
        
        assert resultado.id == visita_id 
        assert resultado.nombre_institucion == "Cliente no disponible"
        assert resultado.direccion == "Dirección no disponible"
        assert resultado.productos_preferidos == []
        assert resultado.notas_visitas_anteriores == []
        assert resultado.cliente_contacto is None

    async def test_actualizar_visita_payload_vacio(self, service: VisitaService, mock_db: Mock):
        visita_id = uuid4()
        data = ActualizarVisitaSchema() 

        mock_visita_db = create_mock_visita(visita_id, uuid4(), uuid4(), "PENDIENTE")
        mock_db.query.return_value.filter.return_value.first.return_value = mock_visita_db

        with pytest.raises(HTTPException) as e:
            await service.actualizar_visita(visita_id, data)
        assert e.value.status_code == HTTPStatus.BAD_REQUEST
        assert "No se proporcionaron datos" in e.value.detail

    @patch("services.visita_service.VisitaService._get_cliente_data", new_callable=AsyncMock)
    @patch("services.visita_service.VisitaService._get_top_products_data", new_callable=AsyncMock)
    @patch("services.visita_service.VisitaService._get_user_contact_for_client", new_callable=AsyncMock)
    @patch("services.visita_service.VisitaService._get_single_route_travel_time", new_callable=AsyncMock)
    async def test_get_visita_detalle_calcula_tiempo_viaje(
        self, mock_get_time: Mock, mock_get_contact: Mock, mock_get_products: Mock, mock_get_cliente: Mock, 
        service: VisitaService, mock_db: Mock
    ):
        """Test: get_visita_detalle_por_id calcula el tiempo de viaje si se provee lat/lon"""
        visita_id = uuid4()
        cliente_id = uuid4()
        mock_visita_db = create_mock_visita(visita_id, cliente_id, uuid4(), "PENDIENTE")
        mock_db.query.return_value.filter.return_value.first.return_value = mock_visita_db
        
        mock_get_cliente.return_value = {"nombre": "Cliente", "address": "7.1,-73.1,Calle"}
        mock_db.query.return_value.filter.return_value.order_by.return_value.limit.return_value.all.return_value = []
        mock_get_products.return_value = []
        mock_get_contact.return_value = "Contacto Prueba"
        
        mock_get_time.return_value = "10 min"

        resultado = await service.get_visita_detalle_por_id(visita_id, lat_actual=7.0, lon_actual=-73.0)

        mock_get_time.assert_called_once_with("7.0,-73.0", "7.1,-73.1")
        assert resultado.tiempo_desplazamiento == "10 min"
        assert resultado.cliente_contacto == "Contacto Prueba"

    @patch("services.visita_service.VisitaService.get_visita_detalle_por_id", new_callable=AsyncMock)
    async def test_actualizar_visita_reprograma_al_cancelar(self, mock_get_detalle: Mock, service: VisitaService, mock_db: Mock):
        """Test: actualizar_visita crea una nueva visita (reprograma) si el estado es CANCELADA"""
        visita_id = uuid4()
        data = ActualizarVisitaSchema(estado="CANCELADA", detalle="Prueba")
        
        mock_visita_db = create_mock_visita(visita_id, uuid4(), uuid4(), "PENDIENTE")
        
        mock_db.query.return_value.filter.return_value.first.return_value = mock_visita_db
        
        mock_get_detalle.return_value = VisitaDetalleResponseSchema(**mock_visita_db.to_dict(), nombre_institucion="Test", direccion="Test")

        await service.actualizar_visita(visita_id, data)
        
        assert mock_db.add.call_count == 2
        mock_db.commit.assert_called_once()
        segunda_llamada_args = mock_db.add.call_args_list[1].args
        assert isinstance(segunda_llamada_args[0], Visita)
        assert segunda_llamada_args[0].estado == "PENDIENTE"