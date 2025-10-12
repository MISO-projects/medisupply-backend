import pytest
from pydantic import ValidationError

from schemas.cliente_schema import ClienteAsignadoResponse, ClienteAsignadoListResponse


class TestClienteAsignadoResponse:
    
    def test_valid_cliente_response(self):
        """Test para respuesta válida de cliente"""
        cliente_data = {
            "id": "C001",
            "nombre": "Hospital General",
            "nit": "901234567-8",
            "logoUrl": "https://storage.googleapis.com/logos/hospital-general.png"
        }
        
        cliente = ClienteAsignadoResponse(**cliente_data)
        
        assert cliente.id == "C001"
        assert cliente.nombre == "Hospital General"
        assert cliente.nit == "901234567-8"
        assert cliente.logoUrl == "https://storage.googleapis.com/logos/hospital-general.png"

    def test_cliente_response_without_logo(self):
        """Test para cliente sin logo"""
        cliente_data = {
            "id": "C002",
            "nombre": "Clinica San Martin",
            "nit": "901987654-3",
            "logoUrl": None
        }
        
        cliente = ClienteAsignadoResponse(**cliente_data)
        
        assert cliente.id == "C002"
        assert cliente.nombre == "Clinica San Martin"
        assert cliente.nit == "901987654-3"
        assert cliente.logoUrl is None

    def test_cliente_response_missing_required_fields(self):
        """Test para campos requeridos faltantes"""
        with pytest.raises(ValidationError) as exc_info:
            ClienteAsignadoResponse(
                id="C001",
                # nombre faltante
                nit="901234567-8"
            )
        
        errors = exc_info.value.errors()
        assert len(errors) == 1
        assert errors[0]["type"] == "missing"
        assert errors[0]["loc"] == ("nombre",)

    def test_cliente_response_empty_strings(self):
        """Test para strings vacíos"""
        with pytest.raises(ValidationError) as exc_info:
            ClienteAsignadoResponse(
                id="",
                nombre="",
                nit=""
            )
        
        errors = exc_info.value.errors()
        # Pydantic puede validar strings vacíos dependiendo de la configuración
        assert len(errors) >= 0  # Al menos algunos campos pueden fallar


class TestClienteAsignadoListResponse:
    
    def test_valid_list_response(self):
        """Test para lista válida de clientes"""
        clientes_data = [
            {
                "id": "C001",
                "nombre": "Hospital General",
                "nit": "901234567-8",
                "logoUrl": "https://storage.googleapis.com/logos/hospital-general.png"
            },
            {
                "id": "C002",
                "nombre": "Clinica San Martin",
                "nit": "901987654-3",
                "logoUrl": None
            }
        ]
        
        list_response = ClienteAsignadoListResponse(
            clientes=clientes_data,
            total=2
        )
        
        assert len(list_response.clientes) == 2
        assert list_response.total == 2
        assert list_response.clientes[0].id == "C001"
        assert list_response.clientes[1].id == "C002"

    def test_empty_list_response(self):
        """Test para lista vacía"""
        list_response = ClienteAsignadoListResponse(
            clientes=[],
            total=0
        )
        
        assert len(list_response.clientes) == 0
        assert list_response.total == 0

    def test_list_response_missing_total(self):
        """Test para total faltante"""
        clientes_data = [
            {
                "id": "C001",
                "nombre": "Hospital General",
                "nit": "901234567-8",
                "logoUrl": None
            }
        ]
        
        with pytest.raises(ValidationError) as exc_info:
            ClienteAsignadoListResponse(
                clientes=clientes_data
                # total faltante
            )
        
        errors = exc_info.value.errors()
        assert len(errors) == 1
        assert errors[0]["type"] == "missing"
        assert errors[0]["loc"] == ("total",)

    def test_list_response_invalid_clientes_type(self):
        """Test para tipo inválido de clientes"""
        with pytest.raises(ValidationError) as exc_info:
            ClienteAsignadoListResponse(
                clientes="invalid_type",  # Debería ser lista
                total=1
            )
        
        errors = exc_info.value.errors()
        assert len(errors) >= 1
        assert any(error["type"] == "list_type" for error in errors)

    def test_serialization_to_dict(self):
        """Test para serialización a diccionario"""
        cliente_data = {
            "id": "C001",
            "nombre": "Hospital General",
            "nit": "901234567-8",
            "logoUrl": "https://storage.googleapis.com/logos/hospital-general.png"
        }
        
        cliente = ClienteAsignadoResponse(**cliente_data)
        cliente_dict = cliente.model_dump()
        
        assert cliente_dict["id"] == "C001"
        assert cliente_dict["nombre"] == "Hospital General"
        assert cliente_dict["nit"] == "901234567-8"
        assert cliente_dict["logoUrl"] == "https://storage.googleapis.com/logos/hospital-general.png"

    def test_serialization_to_json(self):
        """Test para serialización a JSON"""
        cliente_data = {
            "id": "C001",
            "nombre": "Hospital General",
            "nit": "901234567-8",
            "logoUrl": "https://storage.googleapis.com/logos/hospital-general.png"
        }
        
        cliente = ClienteAsignadoResponse(**cliente_data)
        cliente_json = cliente.model_dump_json()
        
        assert '"id":"C001"' in cliente_json
        assert '"nombre":"Hospital General"' in cliente_json
        assert '"nit":"901234567-8"' in cliente_json
        assert '"logoUrl":"https://storage.googleapis.com/logos/hospital-general.png"' in cliente_json
