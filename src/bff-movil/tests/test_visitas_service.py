import pytest
from unittest.mock import Mock, patch, AsyncMock, MagicMock
from fastapi import HTTPException, UploadFile
from http import HTTPStatus
import httpx
from uuid import uuid4
from datetime import date

from services.visitas_service import VisitasService
from schemas.visitas_schema import CrearRutaVisitaSchema

pytestmark = pytest.mark.asyncio

class TestVisitasService:

    @pytest.fixture
    def service(self):
        """Fixture que instancia el servicio con una URL base fake"""
        with patch.dict('os.environ', {'VISITAS_SERVICE_URL': 'http://fake-microservice'}):
            return VisitasService()

    
    @patch("services.visitas_service.httpx.get")
    def test_health_check_success(self, mock_get, service):
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"status": "ok"}
        mock_get.return_value = mock_response

        result = service.health_check()
        assert result == {"status": "ok"}

    @patch("services.visitas_service.httpx.get")
    def test_health_check_failure(self, mock_get, service):
        mock_get.side_effect = httpx.RequestError("Service down")
        with pytest.raises(HTTPException) as e:
            service.health_check()
        assert e.value.status_code == 503


    @patch("services.visitas_service.httpx.AsyncClient")
    async def test_crear_ruta_visita_success(self, mock_client_cls, service):
        mock_client = mock_client_cls.return_value.__aenter__.return_value
        mock_client.post.return_value = Mock(
            status_code=201, 
            json=lambda: {"id": "123", "estado": "PENDIENTE"}
        )

        data = CrearRutaVisitaSchema(cliente_id=uuid4())
        
        result = await service.crear_ruta_visita(data)
        
        assert result["id"] == "123"
        mock_client.post.assert_called_once()
        assert mock_client.post.call_args.kwargs['json']['cliente_id'] == str(data.cliente_id)


    @patch("services.visitas_service.httpx.AsyncClient")
    async def test_actualizar_visita_con_archivo_success(self, mock_client_cls, service):
        """Prueba que el BFF lee el archivo y lo reenvía en 'files'"""
        visita_id = uuid4()
        mock_client = mock_client_cls.return_value.__aenter__.return_value
        mock_client.put.return_value = Mock(
            status_code=200, 
            json=lambda: {"id": str(visita_id), "evidencia": "https://gcs/foto.jpg"}
        )

        mock_file = MagicMock(spec=UploadFile)
        mock_file.filename = "foto_evidencia.jpg"
        mock_file.content_type = "image/jpeg"
        mock_file.read = AsyncMock(return_value=b"contenido_binario_falso")

        result = await service.actualizar_visita(
            visita_id,
            detalle="Prueba BFF",
            archivo_evidencia=mock_file
        )

        assert result["evidencia"] == "https://gcs/foto.jpg"
        
        mock_client.put.assert_called_once()
        call_kwargs = mock_client.put.call_args.kwargs
        
        assert call_kwargs['data']['detalle'] == "Prueba BFF"
        
        enviado_files = call_kwargs['files']
        assert 'evidencia' in enviado_files
        nombre, contenido, tipo = enviado_files['evidencia']
        
        assert nombre == "foto_evidencia.jpg"
        assert contenido == b"contenido_binario_falso" 
        assert tipo == "image/jpeg"

    @patch("services.visitas_service.httpx.AsyncClient")
    async def test_actualizar_visita_microservicio_error_404(self, mock_client_cls, service):
        """Si el microservicio dice 404, el BFF debe responder 404"""
        mock_client = mock_client_cls.return_value.__aenter__.return_value
        
        resp_404 = Mock(status_code=404)
        resp_404.json.return_value = {"detail": "Visita no encontrada"}
        error = httpx.HTTPStatusError("Not Found", request=None, response=resp_404)
        
        mock_client.put.side_effect = error

        with pytest.raises(HTTPException) as e:
            await service.actualizar_visita(uuid4(), detalle="Test")
        
        assert e.value.status_code == 404
        assert e.value.detail == "Visita no encontrada"

    @patch("services.visitas_service.httpx.AsyncClient")
    async def test_actualizar_visita_connection_error(self, mock_client_cls, service):
        """Si el microservicio está caído, BFF responde 503"""
        mock_client = mock_client_cls.return_value.__aenter__.return_value
        mock_client.put.side_effect = httpx.RequestError("Connection refused")

        with pytest.raises(HTTPException) as e:
            await service.actualizar_visita(uuid4(), detalle="Test")
        
        assert e.value.status_code == 503
        assert "No se puede conectar" in e.value.detail

    @patch("services.visitas_service.httpx.AsyncClient")
    async def test_get_rutas_del_dia_success(self, mock_client_cls, service):
        mock_client = mock_client_cls.return_value.__aenter__.return_value
        mock_client.get.return_value = Mock(status_code=200, json=lambda: [])
        
        await service.get_rutas_del_dia(date.today(), uuid4(), 1.0, 1.0)
        
        mock_client.get.assert_called_once()
        params = mock_client.get.call_args.kwargs['params']
        assert 'lat_actual' in params
        assert 'lon_actual' in params

    @patch("services.visitas_service.httpx.AsyncClient")
    async def test_actualizar_visita_solo_texto_success(self, mock_client_cls, service):
        """
        Escenario 1: Actualizar solo texto (SIN ARCHIVO).
        Cubre la lógica cuando 'archivo_evidencia' es None.
        """
        mock_client = mock_client_cls.return_value.__aenter__.return_value
        mock_client.put.return_value = Mock(status_code=200, json=lambda: {"status": "ok"})

        await service.actualizar_visita(
            uuid4(), 
            detalle="Solo texto", 
            archivo_evidencia=None
        )

        call_kwargs = mock_client.put.call_args.kwargs
        assert call_kwargs['files'] is None
        assert call_kwargs['data']['detalle'] == "Solo texto"

    @patch("services.visitas_service.httpx.AsyncClient")
    async def test_crear_ruta_http_error(self, mock_client_cls, service):
        """
        Escenario 2: El microservicio responde con error (ej: 400 Bad Request).
        Cubre: except httpx.HTTPStatusError en crear_ruta_visita
        """
        mock_client = mock_client_cls.return_value.__aenter__.return_value
        
        # Simulamos que el microservicio dice "Datos inválidos"
        resp_400 = Mock(status_code=400)
        resp_400.json.return_value = {"detail": "Cliente inactivo"}
        error = httpx.HTTPStatusError("Bad Request", request=None, response=resp_400)
        
        mock_client.post.side_effect = error

        with pytest.raises(HTTPException) as e:
            await service.crear_ruta_visita(CrearRutaVisitaSchema(cliente_id=uuid4()))
        
        assert e.value.status_code == 400
        assert e.value.detail == {"detail": "Cliente inactivo"}

    @patch("services.visitas_service.httpx.AsyncClient")
    async def test_get_rutas_connection_error(self, mock_client_cls, service):
        """
        Escenario 3: El microservicio está caído o timeout.
        Cubre: except httpx.RequestError en get_rutas_del_dia
        """
        mock_client = mock_client_cls.return_value.__aenter__.return_value
        mock_client.get.side_effect = httpx.RequestError("Timeout connecting")

        with pytest.raises(HTTPException) as e:
            await service.get_rutas_del_dia(date.today(), uuid4(), None, None)
        
        assert e.value.status_code == 503
        assert "No se puede conectar" in e.value.detail

    @patch("services.visitas_service.httpx.AsyncClient")
    async def test_get_detalle_generic_error(self, mock_client_cls, service):
        """
        Escenario 4: Error inesperado (Bug en código o librería).
        Cubre: except Exception en get_visita_detalle
        """
        mock_client = mock_client_cls.return_value.__aenter__.return_value
        # Simulamos un error que NO es de httpx (ej: división por cero o variable nula)
        mock_client.get.side_effect = ValueError("Crash inesperado")

        with pytest.raises(HTTPException) as e:
            await service.get_visita_detalle(uuid4(), None, None)
        
        assert e.value.status_code == 500
        assert "Error interno" in e.value.detail

    @patch("services.visitas_service.httpx.AsyncClient")
    async def test_get_detalle_not_found(self, mock_client_cls, service):
        """
        Escenario 5: Visita no existe (404).
        Cubre: except httpx.HTTPStatusError en get_visita_detalle
        """
        mock_client = mock_client_cls.return_value.__aenter__.return_value
        
        resp_404 = Mock(status_code=404)
        resp_404.json.return_value = "Not found"
        error = httpx.HTTPStatusError("Not found", request=None, response=resp_404)
        
        mock_client.get.side_effect = error

        with pytest.raises(HTTPException) as e:
            await service.get_visita_detalle(uuid4(), None, None)
        
        assert e.value.status_code == 404