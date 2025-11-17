import pytest
from unittest.mock import Mock, AsyncMock
from fastapi.testclient import TestClient
from uuid import uuid4
from http import HTTPStatus
from datetime import datetime, date

from fastapi import HTTPException 

from schemas.visita_schema import (
    CrearRutaVisitaSchema, 
    ActualizarVisitaSchema,
    VisitaDetalleResponseSchema, 
    RutaVisitaItemSchema,
    NotaVisitaAnteriorSchema,
    ProductoPreferidoSchema
)
from typing import List 

pytestmark = pytest.mark.asyncio

class TestVisitaRouter:

    @pytest.mark.asyncio
    async def test_crear_nueva_ruta_visita(self, client: TestClient, mock_visita_service: Mock):
        """Test: Endpoint POST /api/visitas/ (async) - Éxito"""
        cliente_id = uuid4()
        payload = {"cliente_id": str(cliente_id)}
        
        mock_response_data = {
            "id": str(uuid4()),
            "cliente_id": str(cliente_id),
            "vendedor_id": str(uuid4()),
            "fecha_visita_programada": datetime.now().isoformat(),
            "estado": "PENDIENTE",
            "created_at": datetime.now().isoformat()
        }
        mock_visita_service.crear_ruta_visita.return_value = mock_response_data
        
        response = client.post("/api/visitas/", json=payload)
        
        assert response.status_code == HTTPStatus.CREATED
        assert response.json()["cliente_id"] == str(cliente_id)
        mock_visita_service.crear_ruta_visita.assert_called_once_with(
            CrearRutaVisitaSchema(cliente_id=cliente_id)
        )

    @pytest.mark.asyncio
    async def test_get_rutas_por_fecha_y_vendedor(self, client: TestClient, mock_visita_service: Mock):
        """Test: Endpoint GET /api/visitas/rutas-del-dia (async) - Éxito"""
        vendedor_id = uuid4()
        fecha = "2025-10-30"
        
        mock_response_data = [
            RutaVisitaItemSchema(
                id=uuid4(),
                cliente_id=uuid4(),
                nombre="Cliente Test",
                direccion="Calle Falsa 123",
                hora_de_la_cita="10:00",
                estado="PENDIENTE"
            )
        ]
        mock_visita_service.get_rutas_por_fecha_y_vendedor.return_value = mock_response_data
        
        response = client.get(f"/api/visitas/rutas-del-dia?fecha={fecha}&vendedor_id={vendedor_id}")
        
        assert response.status_code == HTTPStatus.OK
        data = response.json()
        assert len(data) == 1
        assert data[0]["nombre"] == "Cliente Test"
        
        mock_visita_service.get_rutas_por_fecha_y_vendedor.assert_called_once_with(
            fecha=date(2025, 10, 30),
            vendedor_id=vendedor_id,
            lat_actual=None,
            lon_actual=None
        )

    @pytest.mark.asyncio
    async def test_get_detalle_visita(self, client: TestClient, mock_visita_service: Mock):
        """Test: Endpoint GET /api/visitas/{visita_id} (async) - Éxito"""
        visita_id = uuid4()
        
        mock_response_data = VisitaDetalleResponseSchema(
            id=visita_id,
            cliente_id=uuid4(),
            vendedor_id=uuid4(),
            fecha_visita_programada=datetime.now(),
            estado="PENDIENTE",
            created_at=datetime.now(),
            nombre_institucion="Institución Detalle",
            direccion="Av. Siempre Viva 742",
            notas_visitas_anteriores=[],
            productos_preferidos=[]
        )
        mock_visita_service.get_visita_detalle_por_id.return_value = mock_response_data
        
        response = client.get(f"/api/visitas/{visita_id}")
        
        assert response.status_code == HTTPStatus.OK
        assert response.json()["nombre_institucion"] == "Institución Detalle"
        
        mock_visita_service.get_visita_detalle_por_id.assert_called_once_with(
            visita_id,         
            lat_actual=None,
            lon_actual=None
        )

    @pytest.mark.asyncio
    async def test_actualizar_visita_endpoint(self, client: TestClient, mock_visita_service: Mock):
        """Test: Endpoint PUT /api/visitas/{visita_id} (async) - Éxito"""
        visita_id = uuid4()
        payload = {"estado": "REALIZADA", "detalle": "Visita completada"}
        
        mock_response_data = VisitaDetalleResponseSchema(
            id=visita_id,
            cliente_id=uuid4(),
            vendedor_id=uuid4(),
            fecha_visita_programada=datetime.now(),
            estado="REALIZADA",
            detalle="Visita completada",
            created_at=datetime.now(),
            updated_at=datetime.now(),
            nombre_institucion="Institución",
            direccion="Dirección",
            notas_visitas_anteriores=[],
            productos_preferidos=[]
        )
        mock_visita_service.actualizar_visita.return_value = mock_response_data
        
        response = client.put(f"/api/visitas/{visita_id}", json=payload)
        
        assert response.status_code == HTTPStatus.OK
        assert response.json()["estado"] == "REALIZADA"
        mock_visita_service.actualizar_visita.assert_called_once_with(
            visita_id,
            ActualizarVisitaSchema(**payload)
        )


    @pytest.mark.asyncio
    async def test_crear_nueva_ruta_visita_cliente_no_encontrado(self, client: TestClient, mock_visita_service: Mock):
        """Test: Endpoint POST / - Falla 404 si el servicio dice que el cliente no existe"""
        
        mock_visita_service.crear_ruta_visita.side_effect = HTTPException(
            status_code=HTTPStatus.NOT_FOUND, detail="Cliente no encontrado."
        )
        
        payload = {"cliente_id": str(uuid4())}
        response = client.post("/api/visitas/", json=payload)
        
        assert response.status_code == HTTPStatus.NOT_FOUND
        assert response.json()["detail"] == "Cliente no encontrado."

    @pytest.mark.asyncio
    async def test_crear_nueva_ruta_visita_uuid_invalido(self, client: TestClient, mock_visita_service: Mock):
        """Test: Endpoint POST / - Falla 422 si el cliente_id no es un UUID"""
        
        payload = {"cliente_id": "esto-no-es-un-uuid"}
        response = client.post("/api/visitas/", json=payload)
        
        assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY
        assert "uuid_parsing" in response.text
        mock_visita_service.crear_ruta_visita.assert_not_called()

    @pytest.mark.asyncio
    async def test_get_detalle_visita_id_invalido(self, client: TestClient, mock_visita_service: Mock):
        """Test: Endpoint GET /{visita_id} - Falla 422 si el ID en la URL no es un UUID"""
        
        response = client.get("/api/visitas/id-invalido")
        
        assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY
        assert "uuid_parsing" in response.text
        mock_visita_service.get_visita_detalle_por_id.assert_not_called()

    @pytest.mark.asyncio
    async def test_get_detalle_visita_no_encontrado(self, client: TestClient, mock_visita_service: Mock):
        """Test: Endpoint GET /{visita_id} - Falla 404 si el servicio no encuentra la visita"""
        visita_id = uuid4()
        
        mock_visita_service.get_visita_detalle_por_id.side_effect = HTTPException(
            status_code=HTTPStatus.NOT_FOUND, detail=f"Visita {visita_id} no encontrada."
        )
        
        response = client.get(f"/api/visitas/{visita_id}")
        
        assert response.status_code == HTTPStatus.NOT_FOUND
        assert response.json()["detail"] == f"Visita {visita_id} no encontrada."

    @pytest.mark.asyncio
    async def test_actualizar_visita_payload_invalido(self, client: TestClient, mock_visita_service: Mock):
        """Test: Endpoint PUT /{visita_id} - Falla 422 si el estado en el body es inválido"""
        visita_id = uuid4()
        
        payload = {"estado": "ESTADO_INVALIDO"}
        response = client.put(f"/api/visitas/{visita_id}", json=payload)
        
        assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY
        assert "Input should be 'PENDIENTE', 'REALIZADA' or 'CANCELADA'" in response.text
        mock_visita_service.actualizar_visita.assert_not_called()