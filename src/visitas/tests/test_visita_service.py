import pytest
from unittest.mock import Mock, patch, AsyncMock, MagicMock
from sqlalchemy.orm import Session
from datetime import date, datetime, timedelta
from uuid import uuid4
from http import HTTPStatus
from fastapi import HTTPException, UploadFile
import httpx

from services.visita_service import VisitaService
from db.visita import Visita
from schemas.visita_schema import CrearRutaVisitaSchema, VisitaDetalleResponseSchema

pytestmark = pytest.mark.asyncio

def create_mock_visita(visita_id: uuid4, cliente_id, vendedor_id, estado="PENDIENTE"):
    fecha = datetime.now()
    mock_visita = Visita(
        cliente_id=cliente_id,
        vendedor_id=vendedor_id,
        fecha_visita_programada=fecha
    )
    mock_visita.id = visita_id 
    mock_visita.estado = estado
    mock_visita.to_dict = lambda: {
        "id": str(visita_id), 
        "cliente_id": str(cliente_id), "vendedor_id": str(vendedor_id),
        "fecha_visita_programada": fecha, "estado": estado, "created_at": fecha, 
        "updated_at": None, "cliente_contacto": None, "detalle": None, 
        "evidencia": None, "inicio": None, "fin": None
    }
    return mock_visita

def mock_db_query_side_effect(pendientes_list, otras_list):
    def query_side_effect(*args): 
        mock_filter = Mock()
        mock_filter.all.return_value = pendientes_list
        mock_filter.order_by.return_value.all.return_value = otras_list
        return mock_filter
    return query_side_effect

class TestVisitaService:

    @pytest.fixture
    def mock_db(self):
        return Mock(spec=Session)

    @pytest.fixture
    def service(self, mock_db: Mock):
        with patch('services.visita_service.get_redis_client') as mock_get_redis:
            mock_redis = Mock()
            mock_get_redis.return_value = mock_redis
            service_instance = VisitaService(db=mock_db)
            service_instance.google_maps_api_key = "fake-key"
            service_instance.bucket_name = "test-bucket"
            service_instance.credentials_path = "dummy.json" 
            yield service_instance

    # --- TESTS DE HELPERS PRIVADOS ---

    @patch("services.visita_service.httpx.AsyncClient")
    async def test_get_cliente_data_success(self, mock_client_cls, service):
        mock_client = mock_client_cls.return_value.__aenter__.return_value
        mock_client.post.return_value = Mock(status_code=200, json=lambda: [{"id": "1", "nombre": "Test"}])
        data = await service._get_cliente_data("1")
        assert data["nombre"] == "Test"

    @patch("services.visita_service.httpx.AsyncClient")
    async def test_get_cliente_data_fail(self, mock_client_cls, service):
        mock_client = mock_client_cls.return_value.__aenter__.return_value
        mock_client.post.side_effect = httpx.RequestError("Error de conexión")
        
        with pytest.raises(HTTPException) as e:
            await service._get_cliente_data("1")
        assert e.value.status_code == 503

    @patch("services.visita_service.storage.Client")
    def test_upload_file_to_gcs_success(self, mock_storage_client, service):
        mock_bucket = Mock()
        mock_blob = Mock()
        mock_client_instance = mock_storage_client.return_value
        mock_client_instance.bucket.return_value = mock_bucket
        mock_bucket.blob.return_value = mock_blob
        
        file = MagicMock(spec=UploadFile)
        file.filename = "foto.jpg"
        file.content_type = "image/jpeg"
        file.file = MagicMock()

        url = service._upload_file_to_gcs(file, custom_name="2025-01-01-ID")
        
        assert url is not None
        assert "https://storage.googleapis.com" in url
        mock_blob.upload_from_file.assert_called_once()


    @patch("services.visita_service.httpx.AsyncClient")
    async def test_crear_ruta_visita_success(self, mock_http_client: Mock, service: VisitaService, mock_db: Mock):
        cliente_id = uuid4()
        vendedor_id = uuid4()
        data = CrearRutaVisitaSchema(cliente_id=cliente_id)
        
        mock_async_client = mock_http_client.return_value.__aenter__.return_value
        mock_async_client.post.return_value = Mock(status_code=200, json=lambda: [{"id": str(cliente_id), "id_vendedor": str(vendedor_id)}])
        
        def side_effect_refresh(obj):
            obj.id = uuid4()
            obj.to_dict = lambda: {"id": str(obj.id), "cliente_id": cliente_id}
        mock_db.refresh.side_effect = side_effect_refresh

        resultado = await service.crear_ruta_visita(data)
        
        mock_db.add.assert_called_once()
        assert resultado["cliente_id"] == cliente_id

    @patch("services.visita_service.httpx.AsyncClient")
    async def test_get_rutas_por_fecha_y_vendedor_success(self, mock_http_client: Mock, service: VisitaService, mock_db: Mock):
        test_fecha = date(2025, 1, 1)
        test_vendedor_id = uuid4()
        cliente_id_1 = uuid4()
        mock_visita_db = create_mock_visita(uuid4(), cliente_id_1, test_vendedor_id, "PENDIENTE")

        mock_db.query.return_value.filter.side_effect = mock_db_query_side_effect([mock_visita_db], [])
        mock_async_client = mock_http_client.return_value.__aenter__.return_value
        mock_async_client.post.return_value = Mock(status_code=200, json=lambda: [{"id": str(cliente_id_1), "nombre": "C", "address": "NA,NA,Dir"}])

        resultados = await service.get_rutas_por_fecha_y_vendedor(test_fecha, test_vendedor_id, 7.0, -73.0)
        assert len(resultados) == 1

    # --- TESTS DE LOGICA DE NEGOCIO / FECHAS / ERRORES ---

    @patch("services.visita_service.httpx.AsyncClient")
    async def test_crear_ruta_calculo_fecha_domingo(self, mock_client_cls, service, mock_db):
        """Prueba: Si es domingo (weekday 6), suma 1 día (Lunes)"""
        domingo = datetime(2023, 10, 29) 
        mock_http = mock_client_cls.return_value.__aenter__.return_value
        mock_http.post.return_value = Mock(status_code=200, json=lambda: [{"id_vendedor": str(uuid4())}])

        with patch("services.visita_service.datetime") as mock_datetime:
            mock_datetime.now.return_value = domingo
            mock_datetime.combine = datetime.combine
            mock_datetime.min = datetime.min
            
            await service.crear_ruta_visita(CrearRutaVisitaSchema(cliente_id=uuid4()))
            
            args = mock_db.add.call_args[0][0]
            assert args.fecha_visita_programada.day == 30

    @patch("services.visita_service.httpx.AsyncClient")
    async def test_get_rutas_google_maps_falla(self, mock_client_cls, service, mock_db):
        """Prueba que el servicio no se rompe si Google Maps da error"""
        visita_id = uuid4()
        mock_visita = create_mock_visita(visita_id, uuid4(), uuid4())
        
        mock_db.query.return_value.filter.side_effect = mock_db_query_side_effect([mock_visita], [])
        
        mock_http = mock_client_cls.return_value.__aenter__.return_value
        resp_clientes = Mock(status_code=200, json=lambda: [{"id": str(mock_visita.cliente_id), "address": "1.0,1.0,Calle"}])
        resp_maps = Mock(status_code=400) # Falla
        
        mock_http.post.return_value = resp_clientes
        mock_http.get.return_value = resp_maps

        res = await service.get_rutas_por_fecha_y_vendedor(date.today(), uuid4(), 1.0, 1.0)
        
        assert len(res) == 1
        # CORREGIDO: Ahora esperamos "Sin calcular" que es lo que devuelve tu código real
        assert res[0].hora_de_la_cita == "Sin calcular"

    @patch("services.visita_service.httpx.AsyncClient")
    async def test_get_rutas_coordenadas_invalidas(self, mock_client_cls, service, mock_db):
        """Prueba que ignora coordenadas corruptas"""
        visita_id = uuid4()
        mock_visita = create_mock_visita(visita_id, uuid4(), uuid4())
        
        mock_db.query.return_value.filter.side_effect = mock_db_query_side_effect([mock_visita], [])
        
        mock_http = mock_client_cls.return_value.__aenter__.return_value
        mock_http.post.return_value = Mock(status_code=200, json=lambda: [{"id": str(mock_visita.cliente_id), "address": "NA,NA"}])

        await service.get_rutas_por_fecha_y_vendedor(date.today(), uuid4(), 1.0, 1.0)
        
        mock_http.get.assert_not_called()

    # --- TESTS ACTUALIZAR ---

    async def test_actualizar_visita_not_found(self, service, mock_db):
        visita_id = uuid4()
        mock_db.query.return_value.filter.return_value.first.return_value = None
        with pytest.raises(HTTPException) as e:
            await service.actualizar_visita(visita_id, estado="REALIZADA")
        assert e.value.status_code == 404

    @patch("services.visita_service.VisitaService.get_visita_detalle_por_id", new_callable=AsyncMock)
    async def test_actualizar_visita_reprograma_al_cancelar(self, mock_get_detalle, service, mock_db):
        visita_id = uuid4()
        cliente_id = uuid4()
        mock_visita_db = create_mock_visita(visita_id, cliente_id, uuid4(), "PENDIENTE")
        mock_db.query.return_value.filter.return_value.first.return_value = mock_visita_db
        mock_get_detalle.return_value = VisitaDetalleResponseSchema(**mock_visita_db.to_dict(), nombre_institucion="T", direccion="T")
        
        await service.actualizar_visita(visita_id, estado="CANCELADA")

        visita_reprogramada = None
        for call in mock_db.add.call_args_list:
            obj = call[0][0]
            if obj.estado == "PENDIENTE" and obj.cliente_id == cliente_id:
                visita_reprogramada = obj
                break
        
        assert visita_reprogramada is not None
        assert mock_visita_db.estado == "CANCELADA"

    @patch("services.visita_service.VisitaService._upload_file_to_gcs")
    @patch("services.visita_service.VisitaService.get_visita_detalle_por_id", new_callable=AsyncMock)
    async def test_actualizar_visita_con_evidencia(self, mock_get_detalle, mock_upload, service, mock_db):
        visita_id = uuid4()
        mock_visita_db = create_mock_visita(visita_id, uuid4(), uuid4(), "PENDIENTE")
        mock_db.query.return_value.filter.return_value.first.return_value = mock_visita_db
        mock_get_detalle.return_value = VisitaDetalleResponseSchema(**mock_visita_db.to_dict(), nombre_institucion="T", direccion="T")
        
        mock_upload.return_value = "https://fake-gcs/foto.jpg"
        mock_file = MagicMock(spec=UploadFile)

        await service.actualizar_visita(
            visita_id,
            detalle="Foto",
            archivo_evidencia=mock_file
        )

        mock_upload.assert_called_once()
        assert mock_visita_db.evidencia == "https://fake-gcs/foto.jpg"
        assert mock_visita_db.estado == "REALIZADA"

    async def test_actualizar_visita_error_interno(self, service, mock_db):
        visita_id = uuid4()
        mock_db.query.side_effect = Exception("DB Crash")
        
        with pytest.raises(HTTPException) as e:
            await service.actualizar_visita(visita_id)
        assert e.value.status_code == 500