import pytest
from unittest.mock import Mock, MagicMock, patch
from fastapi import HTTPException
from datetime import datetime
import uuid
import json

from db.proveedor_model import Proveedor
from schemas.proveedor_schema import (
    CrearProveedorSchema,
    ActualizarProveedorSchema,
    PaisEnum,
    TipoProveedorEnum
)


def get_service(mock_db, mock_redis=None):
    """Helper function to get service instance"""
    with patch('services.proveedor_service.get_redis_client') as mock_get_redis:
        mock_get_redis.return_value = mock_redis
        from services.proveedor_service import ProveedorService
        return ProveedorService(db=mock_db)


@pytest.fixture
def mock_db():
    """Fixture para crear un mock de la sesión de base de datos"""
    db = MagicMock()
    db.query.return_value = db
    db.filter.return_value = db
    db.offset.return_value = db
    db.limit.return_value = db
    db.order_by.return_value = db
    return db


@pytest.fixture
def mock_redis():
    """Fixture para crear un mock del cliente Redis"""
    redis_mock = MagicMock()
    redis_mock.get.return_value = None  # Default: no cache hit
    redis_mock.setex.return_value = True
    redis_mock.delete.return_value = 0
    redis_mock.keys.return_value = []
    return redis_mock


@pytest.fixture
def valid_proveedor_data():
    """Fixture con datos válidos de proveedor"""
    return CrearProveedorSchema(
        nombre="Farmacéutica Nacional S.A.",
        id_tributario="20123456789",
        tipo_proveedor=TipoProveedorEnum.FABRICANTE,
        email="contacto@farmaceutica.com",
        pais=PaisEnum.PERU,
        contacto="Juan Pérez - +51 999 888 777",
        condiciones_entrega="Entrega en 5 días hábiles"
    )


@pytest.fixture
def mock_proveedor():
    """Fixture para crear un mock de proveedor"""
    proveedor = Mock(spec=Proveedor)
    proveedor.id = uuid.uuid4()
    proveedor.fecha_creacion = datetime.now()
    proveedor.fecha_actualizacion = datetime.now()
    proveedor.nombre = "Farmacéutica Nacional S.A."
    proveedor.id_tributario = "20123456789"
    proveedor.tipo_proveedor = "Fabricante"
    proveedor.email = "contacto@farmaceutica.com"
    proveedor.pais = "Perú"
    proveedor.contacto = "Juan Pérez"
    proveedor.condiciones_entrega = "Entrega en 5 días"
    
    proveedor.to_dict.return_value = {
        "id": str(proveedor.id),
        "fecha_creacion": proveedor.fecha_creacion.isoformat(),
        "fecha_actualizacion": proveedor.fecha_actualizacion.isoformat(),
        "nombre": proveedor.nombre,
        "id_tributario": proveedor.id_tributario,
        "tipo_proveedor": proveedor.tipo_proveedor,
        "email": proveedor.email,
        "pais": proveedor.pais,
        "contacto": proveedor.contacto,
        "condiciones_entrega": proveedor.condiciones_entrega
    }
    
    return proveedor


class TestCrearProveedor:
    """Tests para la creación de proveedores"""
    
    def test_crear_proveedor_exitoso(self, mock_db, mock_redis, valid_proveedor_data, mock_proveedor):
        """Test: Crear un proveedor exitosamente"""
        # Arrange
        proveedor_service = get_service(mock_db, mock_redis)
        mock_db.first.return_value = None  # No existe proveedor duplicado
        
        # Act
        result = proveedor_service.crear_proveedor(valid_proveedor_data)
        
        # Assert
        assert mock_db.add.called
        assert mock_db.commit.called
        assert "nombre" in result
        assert mock_redis.keys.called
        
    def test_crear_proveedor_id_tributario_duplicado(self, mock_db, mock_redis, valid_proveedor_data, mock_proveedor):
        """Test: Error al crear proveedor con ID tributario duplicado"""
        # Arrange
        proveedor_service = get_service(mock_db, mock_redis)
        mock_db.first.return_value = mock_proveedor  # Ya existe
        
        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            proveedor_service.crear_proveedor(valid_proveedor_data)
        
        assert exc_info.value.status_code == 409
        assert "ID tributario" in exc_info.value.detail
        
    def test_crear_proveedor_email_duplicado(self, mock_db, mock_redis, valid_proveedor_data, mock_proveedor):
        """Test: Error al crear proveedor con email duplicado"""
        # Arrange
        proveedor_service = get_service(mock_db, mock_redis)
        # Primera llamada (id_tributario) retorna None, segunda (email) retorna proveedor
        mock_db.first.side_effect = [None, mock_proveedor]
        
        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            proveedor_service.crear_proveedor(valid_proveedor_data)
        
        assert exc_info.value.status_code == 409
        assert "email" in exc_info.value.detail.lower()


class TestObtenerProveedor:
    """Tests para obtener un proveedor"""
    
    def test_obtener_proveedor_existente_sin_cache(self, mock_db, mock_redis, mock_proveedor):
        """Test: Obtener un proveedor que existe (cache miss)"""
        # Arrange
        proveedor_service = get_service(mock_db, mock_redis)
        proveedor_id = str(uuid.uuid4())
        mock_db.first.return_value = mock_proveedor
        mock_redis.get.return_value = None  # Cache miss
        
        # Act
        result = proveedor_service.obtener_proveedor(proveedor_id)
        
        # Assert
        assert result is not None
        assert "nombre" in result
        assert mock_db.first.called  # DB was queried
        assert mock_redis.setex.called  # Cache was set
        
    def test_obtener_proveedor_desde_cache(self, mock_db, mock_redis, mock_proveedor):
        """Test: Obtener un proveedor desde cache (cache hit)"""
        # Arrange
        proveedor_service = get_service(mock_db, mock_redis)
        proveedor_id = str(uuid.uuid4())
        cached_data = mock_proveedor.to_dict()
        mock_redis.get.return_value = json.dumps(cached_data)
        
        # Act
        result = proveedor_service.obtener_proveedor(proveedor_id)
        
        # Assert
        assert result is not None
        assert "nombre" in result
        assert not mock_db.first.called  # DB was NOT queried
        
    def test_obtener_proveedor_no_existente(self, mock_db, mock_redis):
        """Test: Error al obtener un proveedor que no existe"""
        # Arrange
        proveedor_service = get_service(mock_db, mock_redis)
        proveedor_id = str(uuid.uuid4())
        mock_db.first.return_value = None
        mock_redis.get.return_value = None
        
        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            proveedor_service.obtener_proveedor(proveedor_id)
        
        assert exc_info.value.status_code == 404


class TestListarProveedores:
    """Tests para listar proveedores"""
    
    def test_listar_proveedores_sin_filtros(self, mock_db, mock_redis, mock_proveedor):
        """Test: Listar todos los proveedores sin filtros"""
        # Arrange
        proveedor_service = get_service(mock_db, mock_redis)
        mock_db.all.return_value = [mock_proveedor, mock_proveedor]
        mock_redis.get.return_value = None  # Cache miss
        
        # Act
        result = proveedor_service.listar_proveedores()
        
        # Assert
        assert isinstance(result, list)
        assert len(result) == 2
        assert mock_redis.setex.called  # Cache was set
        
    def test_listar_proveedores_con_filtro_pais(self, mock_db, mock_redis, mock_proveedor):
        """Test: Listar proveedores filtrados por país"""
        # Arrange
        proveedor_service = get_service(mock_db, mock_redis)
        mock_db.all.return_value = [mock_proveedor]
        mock_redis.get.return_value = None  # Cache miss
        
        # Act
        result = proveedor_service.listar_proveedores(pais="Perú")
        
        # Assert
        assert mock_db.filter.called
        assert len(result) == 1
        
    def test_listar_proveedores_con_paginacion(self, mock_db, mock_redis, mock_proveedor):
        """Test: Listar proveedores con paginación"""
        # Arrange
        proveedor_service = get_service(mock_db, mock_redis)
        mock_db.all.return_value = [mock_proveedor]
        mock_redis.get.return_value = None  # Cache miss
        
        # Act
        result = proveedor_service.listar_proveedores(skip=10, limit=5)
        
        # Assert
        assert mock_db.offset.called
        assert mock_db.limit.called
        
    def test_listar_proveedores_desde_cache(self, mock_db, mock_redis, mock_proveedor):
        """Test: Listar proveedores desde cache (cache hit)"""
        # Arrange
        proveedor_service = get_service(mock_db, mock_redis)
        cached_data = [mock_proveedor.to_dict()]
        mock_redis.get.return_value = json.dumps(cached_data)
        
        # Act
        result = proveedor_service.listar_proveedores()
        
        # Assert
        assert isinstance(result, list)
        assert len(result) == 1
        assert not mock_db.all.called  # DB was NOT queried


class TestActualizarProveedor:
    """Tests para actualizar proveedores"""
    
    def test_actualizar_proveedor_exitoso(self, mock_db, mock_redis, mock_proveedor):
        """Test: Actualizar un proveedor exitosamente"""
        # Arrange
        proveedor_service = get_service(mock_db, mock_redis)
        proveedor_id = str(uuid.uuid4())
        mock_db.first.return_value = mock_proveedor
        update_data = ActualizarProveedorSchema(
            nombre="Nuevo Nombre S.A.C."
        )
        
        # Act
        result = proveedor_service.actualizar_proveedor(proveedor_id, update_data)
        
        # Assert
        assert mock_db.commit.called
        assert result is not None
        assert mock_redis.keys.called
        
    def test_actualizar_proveedor_no_existente(self, mock_db, mock_redis):
        """Test: Error al actualizar un proveedor que no existe"""
        # Arrange
        proveedor_service = get_service(mock_db, mock_redis)
        proveedor_id = str(uuid.uuid4())
        mock_db.first.return_value = None
        update_data = ActualizarProveedorSchema(nombre="Nuevo Nombre")
        
        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            proveedor_service.actualizar_proveedor(proveedor_id, update_data)
        
        assert exc_info.value.status_code == 404
        
    def test_actualizar_proveedor_email_duplicado(self, mock_db, mock_redis, mock_proveedor):
        """Test: Error al actualizar con email que ya existe"""
        # Arrange
        proveedor_service = get_service(mock_db, mock_redis)
        proveedor_id = str(uuid.uuid4())
        otro_proveedor = Mock(spec=Proveedor)
        otro_proveedor.email = "otro@email.com"
        
        mock_db.first.side_effect = [mock_proveedor, otro_proveedor]
        update_data = ActualizarProveedorSchema(email="otro@email.com")
        
        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            proveedor_service.actualizar_proveedor(proveedor_id, update_data)
        
        assert exc_info.value.status_code == 409


class TestEliminarProveedor:
    """Tests para eliminar proveedores"""
    
    def test_eliminar_proveedor_exitoso(self, mock_db, mock_redis, mock_proveedor):
        """Test: Eliminar un proveedor exitosamente"""
        # Arrange
        proveedor_service = get_service(mock_db, mock_redis)
        proveedor_id = str(uuid.uuid4())
        mock_db.first.return_value = mock_proveedor
        
        # Act
        result = proveedor_service.eliminar_proveedor(proveedor_id)
        
        # Assert
        assert mock_db.delete.called
        assert mock_db.commit.called
        assert "message" in result
        assert mock_redis.keys.called
        
    def test_eliminar_proveedor_no_existente(self, mock_db, mock_redis):
        """Test: Error al eliminar un proveedor que no existe"""
        # Arrange
        proveedor_service = get_service(mock_db, mock_redis)
        proveedor_id = str(uuid.uuid4())
        mock_db.first.return_value = None
        
        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            proveedor_service.eliminar_proveedor(proveedor_id)
        
        assert exc_info.value.status_code == 404


class TestContarProveedores:
    """Tests para contar proveedores"""
    
    def test_contar_proveedores_sin_filtros(self, mock_db, mock_redis):
        """Test: Contar todos los proveedores"""
        # Arrange
        proveedor_service = get_service(mock_db, mock_redis)
        mock_db.count.return_value = 10
        mock_redis.get.return_value = None  # Cache miss
        
        # Act
        result = proveedor_service.contar_proveedores()
        
        # Assert
        assert result == 10
        assert mock_redis.setex.called  # Cache was set
        
    def test_contar_proveedores_con_filtros(self, mock_db, mock_redis):
        """Test: Contar proveedores con filtros"""
        # Arrange
        proveedor_service = get_service(mock_db, mock_redis)
        mock_db.count.return_value = 5
        mock_redis.get.return_value = None  # Cache miss
        
        # Act
        result = proveedor_service.contar_proveedores(pais="Perú", tipo_proveedor="Fabricante")
        
        # Assert
        assert mock_db.filter.called
        assert result == 5
        
    def test_contar_proveedores_desde_cache(self, mock_db, mock_redis):
        """Test: Contar proveedores desde cache (cache hit)"""
        # Arrange
        proveedor_service = get_service(mock_db, mock_redis)
        mock_redis.get.return_value = json.dumps(15)
        
        # Act
        result = proveedor_service.contar_proveedores()
        
        # Assert
        assert result == 15
        assert not mock_db.count.called  # DB was NOT queried


class TestCacheGracefulDegradation:
    """Tests para verificar degradación graciosa cuando Redis no está disponible"""
    
    def test_obtener_proveedor_sin_redis(self, mock_db, mock_proveedor):
        """Test: Obtener proveedor funciona sin Redis disponible"""
        # Arrange
        proveedor_service = get_service(mock_db, None)  # Redis is None
        proveedor_id = str(uuid.uuid4())
        mock_db.first.return_value = mock_proveedor
        
        # Act
        result = proveedor_service.obtener_proveedor(proveedor_id)
        
        # Assert
        assert result is not None
        assert "nombre" in result
        assert mock_db.first.called
        
    def test_listar_proveedores_sin_redis(self, mock_db, mock_proveedor):
        """Test: Listar proveedores funciona sin Redis disponible"""
        # Arrange
        proveedor_service = get_service(mock_db, None)  # Redis is None
        mock_db.all.return_value = [mock_proveedor]
        
        # Act
        result = proveedor_service.listar_proveedores()
        
        # Assert
        assert isinstance(result, list)
        assert len(result) == 1
        
    def test_crear_proveedor_sin_redis(self, mock_db, valid_proveedor_data):
        """Test: Crear proveedor funciona sin Redis disponible"""
        # Arrange
        proveedor_service = get_service(mock_db, None)  # Redis is None
        mock_db.first.return_value = None
        
        # Act
        result = proveedor_service.crear_proveedor(valid_proveedor_data)
        
        # Assert
        assert mock_db.add.called
        assert mock_db.commit.called
        
    def test_cache_error_handling(self, mock_db, mock_redis, mock_proveedor):
        """Test: Manejar errores de Redis graciosamente"""
        # Arrange
        proveedor_service = get_service(mock_db, mock_redis)
        proveedor_id = str(uuid.uuid4())
        mock_db.first.return_value = mock_proveedor
        mock_redis.get.side_effect = Exception("Redis connection error")
        
        # Act
        result = proveedor_service.obtener_proveedor(proveedor_id)
        
        assert result is not None
        assert "nombre" in result
        assert mock_db.first.called

