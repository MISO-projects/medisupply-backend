import pytest
from unittest.mock import Mock, patch
from sqlalchemy.orm import Session
from datetime import datetime, timezone
import uuid

from services.cliente_service import ClienteService
from models.cliente_institucional_model import ClienteInstitucional
from schemas.cliente_schema import ClienteAsignadoResponse, ClienteAsignadoListResponse
from db.redis_client import RedisClient
from schemas.cliente_schema import RegisterRequest


class TestClienteService:
    
    @pytest.fixture
    def mock_db(self):
        return Mock(spec=Session)
    
    @pytest.fixture
    def mock_redis_client(self):
        redis_client = Mock(spec=RedisClient)
        redis_client.is_connected.return_value = True
        redis_client.client = Mock()
        return redis_client
    
    @pytest.fixture
    def cliente_service(self, mock_db, mock_redis_client):
        return ClienteService(db=mock_db, redis_client=mock_redis_client)
    
    @pytest.fixture
    def sample_cliente_data(self):
        cliente_id = str(uuid.uuid4())
        vendedor_id = str(uuid.uuid4())
        
        cliente = ClienteInstitucional(
            nombre="Hospital General",
            nit="901234567-8",
            id_vendedor=vendedor_id,
            logo_url="https://storage.googleapis.com/logos/hospital-general.png",
            address="Calle 45 #10-20, Cartagena" 
        )
        cliente.id = uuid.UUID(cliente_id)
        return cliente, vendedor_id

    def test_get_clientes_asignados_success(self, cliente_service, mock_db, mock_redis_client, sample_cliente_data):
        """Test exitoso para obtener clientes asignados"""
        cliente, vendedor_id = sample_cliente_data
        
        # Mock de la consulta a la base de datos
        mock_db.query.return_value.filter.return_value.all.return_value = [cliente]
        
        # Mock de Redis (sin cache)
        mock_redis_client.client.get.return_value = None
        
        # Ejecutar método
        result = cliente_service.get_clientes_asignados(vendedor_id)
        
        # Verificaciones
        assert isinstance(result, ClienteAsignadoListResponse)
        assert result.total == 1
        assert len(result.clientes) == 1
        assert result.clientes[0].id == str(cliente.id)
        assert result.clientes[0].nombre == cliente.nombre
        assert result.clientes[0].nit == cliente.nit
        assert result.clientes[0].logoUrl == cliente.logo_url
        
        # Verificar que se guardó en cache
        mock_redis_client.client.setex.assert_called_once()

    def test_get_clientes_asignados_from_cache(self, cliente_service, mock_db, mock_redis_client, sample_cliente_data):
        """Test para obtener clientes desde cache"""
        cliente, vendedor_id = sample_cliente_data
        
        # Mock de datos en cache
        cached_response = ClienteAsignadoListResponse(
            clientes=[
                ClienteAsignadoResponse(
                    id=str(cliente.id),
                    nombre=cliente.nombre,
                    nit=cliente.nit,
                    logoUrl=cliente.logo_url
                )
            ],
            total=1
        )
        
        mock_redis_client.client.get.return_value = cached_response.model_dump_json()
        
        # Ejecutar método
        result = cliente_service.get_clientes_asignados(vendedor_id)
        
        # Verificaciones
        assert isinstance(result, ClienteAsignadoListResponse)
        assert result.total == 1
        assert len(result.clientes) == 1
        
        # Verificar que NO se consultó la base de datos
        mock_db.query.assert_not_called()

    def test_get_clientes_asignados_empty_list(self, cliente_service, mock_db, mock_redis_client):
        """Test para cuando no hay clientes asignados"""
        vendedor_id = str(uuid.uuid4())
        
        # Mock de consulta vacía
        mock_db.query.return_value.filter.return_value.all.return_value = []
        mock_redis_client.client.get.return_value = None
        
        # Ejecutar método
        result = cliente_service.get_clientes_asignados(vendedor_id)
        
        # Verificaciones
        assert isinstance(result, ClienteAsignadoListResponse)
        assert result.total == 0
        assert len(result.clientes) == 0

    def test_get_cliente_by_id_success(self, cliente_service, mock_db, sample_cliente_data):
        """Test exitoso para obtener cliente por ID"""
        cliente, vendedor_id = sample_cliente_data
        
        # Mock de la consulta
        mock_db.query.return_value.filter.return_value.first.return_value = cliente
        
        # Ejecutar método
        result = cliente_service.get_cliente_by_id(str(cliente.id), vendedor_id)
        
        # Verificaciones
        assert isinstance(result, ClienteAsignadoResponse)
        assert result.id == str(cliente.id)
        assert result.nombre == cliente.nombre
        assert result.nit == cliente.nit
        assert result.logoUrl == cliente.logo_url

    def test_get_cliente_by_id_not_found(self, cliente_service, mock_db):
        """Test cuando el cliente no existe o no está asignado"""
        cliente_id = str(uuid.uuid4())
        vendedor_id = str(uuid.uuid4())
        
        # Mock de consulta sin resultados
        mock_db.query.return_value.filter.return_value.first.return_value = None
        
        # Ejecutar método
        result = cliente_service.get_cliente_by_id(cliente_id, vendedor_id)
        
        # Verificaciones
        assert result is None

    def test_invalidate_cache(self, cliente_service, mock_redis_client):
        """Test para invalidar cache"""
        vendedor_id = str(uuid.uuid4())
        
        # Ejecutar método
        cliente_service.invalidate_cache(vendedor_id)
        
        # Verificaciones
        mock_redis_client.client.delete.assert_called_once_with(f"clientes_asignados:{vendedor_id}")

    def test_redis_not_connected(self, cliente_service, mock_db, mock_redis_client, sample_cliente_data):
        """Test cuando Redis no está conectado"""
        cliente, vendedor_id = sample_cliente_data
        
        # Mock de Redis desconectado
        mock_redis_client.is_connected.return_value = False
        mock_db.query.return_value.filter.return_value.all.return_value = [cliente]
        
        # Ejecutar método
        result = cliente_service.get_clientes_asignados(vendedor_id)
        
        # Verificaciones
        assert isinstance(result, ClienteAsignadoListResponse)
        assert result.total == 1
        
        # Verificar que no se intentó usar Redis
        mock_redis_client.client.get.assert_not_called()
        mock_redis_client.client.setex.assert_not_called()

    def test_get_all_clients_success(self, mock_db):
        cliente = Mock()
        cliente.id = uuid.uuid4()
        cliente.nombre = "Clinica ABC"
        cliente.nit = "900111222-3"
        cliente.logo_url = "https://example.com/logo.png"
        cliente.address = "Cra 10 #20-30"
        cliente.fecha_creacion = "2025-01-01"
        cliente.fecha_actualizacion = "2025-02-01"
        cliente.id_vendedor = uuid.uuid4()

        mock_db.query.return_value.all.return_value = [cliente]
        service = ClienteService(db=mock_db, redis_client=Mock())

        result = service.get_all_clients(mock_db)
        assert len(result) == 1
        assert result[0].nombre == "Clinica ABC"

    def test_get_all_clients_error(self, mock_db):
        mock_db.query.side_effect = Exception("DB error")
        service = ClienteService(db=mock_db, redis_client=Mock())

        with pytest.raises(Exception):
            service.get_all_clients(mock_db)

    
    def test_register_client_success(self, mock_db):
        data = RegisterRequest(
            nombre="Nuevo Cliente",
            nit="900555666-7",
            address="Cra 1 #1-1",
            logoUrl="https://logo.com"
        )
        new_client = Mock()
        new_client.to_dict.return_value = {
            "id": str(uuid.uuid4()),
            "nombre": data.nombre,
            "nit": data.nit,
            "logoUrl": data.logoUrl,
            "address": data.address,
            "id_vendedor": None,
            "fecha_creacion": "2025-01-01T00:00:00Z",  
            "fecha_actualizacion": "2025-01-01T00:00:00Z"  
        }

        mock_db.refresh.side_effect = lambda x: x.__setattr__('to_dict', new_client.to_dict)
        service = ClienteService(db=mock_db, redis_client=Mock())
        
        result = service.register_client(mock_db, data)
        assert result.nombre == data.nombre
        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()


