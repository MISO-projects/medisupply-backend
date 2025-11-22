import pytest
from unittest.mock import Mock, AsyncMock
from fastapi.testclient import TestClient
from uuid import uuid4
from http import HTTPStatus
from datetime import datetime, date

from schemas.visita_schema import (
    CrearRutaVisitaSchema, 
    VisitaDetalleResponseSchema, 
    RutaVisitaItemSchema
)

pytestmark = pytest.mark.asyncio

class TestVisitaRouter:

    @pytest.mark.asyncio
    async def test_crear_nueva_ruta_visita(self, client: TestClient, mock_visita_service: Mock):
        cliente_id = uuid4()
        payload = {"cliente_id": str(cliente_id)}
        mock_response = {"id": str(uuid4()), "cliente_id": str(cliente_id), "vendedor_id": str(uuid4()), "fecha_visita_programada": datetime.now(), "estado": "PENDIENTE", "created_at": datetime.now()}
        mock_visita_service.crear_ruta_visita.return_value = mock_response
        
        response = client.post("/api/visitas/", json=payload)
        assert response.status_code == HTTPStatus.CREATED

    @pytest.mark.asyncio
    async def test_get_rutas_por_fecha(self, client: TestClient, mock_visita_service: Mock):
        mock_visita_service.get_rutas_por_fecha_y_vendedor.return_value = []
        response = client.get(f"/api/visitas/rutas-del-dia?fecha=2025-01-01&vendedor_id={uuid4()}")
        assert response.status_code == 200
    @pytest.mark.asyncio
    async def test_crear_ruta_visita_error_interno(self, client: TestClient, mock_visita_service: Mock):
        """Test: Simula un crash inesperado en el servicio (500)"""
        mock_visita_service.crear_ruta_visita.side_effect = Exception("Error inesperado DB")
        
        response = client.post("/api/visitas/", json={"cliente_id": str(uuid4())})
        
        assert response.status_code == HTTPStatus.INTERNAL_SERVER_ERROR
        assert "Error inesperado DB" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_get_rutas_error_interno(self, client: TestClient, mock_visita_service: Mock):
        """Test: Simula crash en get rutas"""
        mock_visita_service.get_rutas_por_fecha_y_vendedor.side_effect = Exception("Boom")
        
        response = client.get(f"/api/visitas/rutas-del-dia?fecha=2025-01-01&vendedor_id={uuid4()}")
        
        assert response.status_code == HTTPStatus.INTERNAL_SERVER_ERROR

    @pytest.mark.asyncio
    async def test_actualizar_visita_error_interno(self, client: TestClient, mock_visita_service: Mock):
        """Test: Simula crash en actualizar"""
        mock_visita_service.actualizar_visita.side_effect = Exception("Fallo al subir archivo")
        
        response = client.put(f"/api/visitas/{uuid4()}", data={"estado": "REALIZADA"})
        
        assert response.status_code == HTTPStatus.INTERNAL_SERVER_ERROR
        
    @pytest.mark.asyncio
    async def test_actualizar_visita_endpoint_con_archivo(self, client: TestClient, mock_visita_service: Mock):
        """Test: Endpoint PUT recibiendo archivo y datos"""
        visita_id = uuid4()
        
        # Mock de respuesta
        mock_resp = VisitaDetalleResponseSchema(
            id=visita_id, cliente_id=uuid4(), vendedor_id=uuid4(), fecha_visita_programada=datetime.now(),
            estado="REALIZADA", created_at=datetime.now(), nombre_institucion="T", direccion="T", 
            notas_visitas_anteriores=[], productos_preferidos=[]
        )
        mock_visita_service.actualizar_visita.return_value = mock_resp

        # Simular envío Multipart
        files = {'evidencia': ('test.jpg', b'bytes', 'image/jpeg')}
        data = {'estado': 'REALIZADA', 'detalle': 'Test'}

        response = client.put(f"/api/visitas/{visita_id}", data=data, files=files)
        
        assert response.status_code == 200
        
        # Verificar que se llamó al servicio
        mock_visita_service.actualizar_visita.assert_called_once()
        kwargs = mock_visita_service.actualizar_visita.call_args.kwargs
        assert kwargs['estado'] == 'REALIZADA'
        assert kwargs['archivo_evidencia'] is not None