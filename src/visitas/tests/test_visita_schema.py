import pytest
from pydantic import ValidationError
from uuid import uuid4
from datetime import datetime

from schemas.visita_schema import (
    CrearRutaVisitaSchema,
    RutaVisitaItemSchema,
    VisitaDetalleResponseSchema,
    EstadoVisitaEnum
)

class TestRequestSchemas:
    """Prueba los schemas de Pydantic para los 'requests' (entradas)"""

    def test_crear_ruta_visita_schema_valid(self):
        cliente_id = uuid4()
        data = {"cliente_id": cliente_id}
        schema = CrearRutaVisitaSchema(**data)
        assert schema.cliente_id == cliente_id

    def test_crear_ruta_visita_schema_invalid(self):
        with pytest.raises(ValidationError) as e:
            CrearRutaVisitaSchema()
        assert any(err['loc'] == ('cliente_id',) and err['type'] == 'missing' for err in e.value.errors())

    def test_crear_ruta_visita_schema_uuid_invalido(self):
        with pytest.raises(ValidationError):
            CrearRutaVisitaSchema(cliente_id="12345")

class TestResponseSchemas:
    """Prueba los schemas de Pydantic para los 'responses' (salidas)"""

    def test_ruta_visita_item_schema_valid(self):
        data = {
            "id": uuid4(),
            "cliente_id": uuid4(),
            "nombre": "Cliente Test",
            "direccion": "Calle Falsa 123",
            "hora_de_la_cita": "09:30",
            "estado": "PENDIENTE"
        }
        schema = RutaVisitaItemSchema(**data)
        assert schema.nombre == "Cliente Test"

    def test_visita_detalle_response_schema_valid(self):
        data = {
            "id": uuid4(),
            "cliente_id": uuid4(),
            "fecha_visita_programada": datetime.now(),
            "vendedor_id": uuid4(),
            "estado": "PENDIENTE",
            "created_at": datetime.now(),
            "nombre_institucion": "Institución Test",
            "direccion": "Av. Siempre Viva 742",
            "notas_visitas_anteriores": [],
            "productos_preferidos": [],
            "tiempo_desplazamiento": "15 min"
        }
        schema = VisitaDetalleResponseSchema(**data)
        assert schema.nombre_institucion == "Institución Test"
    def test_ruta_visita_item_schema_campos_nulos(self):
        data = {
            "id": uuid4(),
            "cliente_id": uuid4(),
            "nombre": "Cliente Sin Dirección",
            "direccion": None, 
            "hora_de_la_cita": "10:00",
            "estado": "REALIZADA"
        }
        schema = RutaVisitaItemSchema(**data)
        assert schema.nombre == "Cliente Sin Dirección"
        assert schema.direccion is None