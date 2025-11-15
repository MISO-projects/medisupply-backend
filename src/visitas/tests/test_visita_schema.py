import pytest
from pydantic import ValidationError
from uuid import uuid4
from datetime import datetime

from schemas.visita_schema import (
    CrearRutaVisitaSchema,
    ActualizarVisitaSchema,
    RutaVisitaItemSchema,
    VisitaDetalleResponseSchema,
    EstadoVisitaEnum,
    NotaVisitaAnteriorSchema, 
    ProductoPreferidoSchema  
)

class TestRequestSchemas:
    """Prueba los schemas de Pydantic para los 'requests' (entradas)"""

    def test_crear_ruta_visita_schema_valid(self):
        """Test: Creación válida de schema de crear ruta"""
        cliente_id = uuid4()
        data = {"cliente_id": cliente_id}
        schema = CrearRutaVisitaSchema(**data)
        assert schema.cliente_id == cliente_id

    def test_crear_ruta_visita_schema_invalid(self):
        """Test: Falla si falta cliente_id"""
        with pytest.raises(ValidationError) as e:
            CrearRutaVisitaSchema()
        assert any(err['loc'] == ('cliente_id',) and err['type'] == 'missing' for err in e.value.errors())

    def test_actualizar_visita_schema_valid(self):
        """Test: Creación válida de schema de actualizar visita"""
        data = {
            "estado": "REALIZADA",
            "detalle": "Visita completada exitosamente."
        }
        schema = ActualizarVisitaSchema(**data)
        assert schema.estado == EstadoVisitaEnum.REALIZADA
        assert schema.detalle == "Visita completada exitosamente."

    def test_actualizar_visita_schema_estado_invalido(self):
        """Test: Falla si el estado no está en el Enum"""
        with pytest.raises(ValidationError):
            ActualizarVisitaSchema(estado="ESTADO_INVALIDO")

    def test_actualizar_visita_schema_campos_opcionales(self):
        """Test: Todos los campos son opcionales"""
        schema = ActualizarVisitaSchema()
        assert schema.inicio is None
        assert schema.estado is None

    def test_actualizar_visita_schema_max_length(self):
        """Test: Falla si se supera el max_length"""
        with pytest.raises(ValidationError, match="100 characters"):
            ActualizarVisitaSchema(detalle="x" * 101) # Asumiendo max_length=100
        with pytest.raises(ValidationError, match="100 characters"):
            ActualizarVisitaSchema(cliente_contacto="x" * 101)

    def test_crear_ruta_visita_schema_uuid_invalido(self):
        """Test: Falla si cliente_id no es un UUID válido"""
        with pytest.raises(ValidationError):
            CrearRutaVisitaSchema(cliente_id="12345")

    def test_actualizar_visita_schema_evidencia_max_length(self):
        """Test: Falla si el campo 'evidencia' supera el max_length"""
        with pytest.raises(ValidationError, match="100 characters"):
            ActualizarVisitaSchema(evidencia="http://example.com/" + ("x" * 101))


class TestResponseSchemas:
    """Prueba los schemas de Pydantic para los 'responses' (salidas)"""

    def test_ruta_visita_item_schema_valid(self):
        """Test: Creación válida del response schema de item de ruta"""
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
        assert schema.hora_de_la_cita == "09:30"

    def test_visita_detalle_response_schema_valid(self):
        """Test: Creación válida del response schema de detalle"""
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
        assert schema.estado == "PENDIENTE"
        assert schema.tiempo_desplazamiento == "15 min"

    
    def test_ruta_visita_item_schema_campos_nulos(self):
        """Test: Valida que los campos opcionales (direccion) pueden ser None"""
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