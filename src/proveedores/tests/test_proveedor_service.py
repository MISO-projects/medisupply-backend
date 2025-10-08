import pytest
from unittest.mock import Mock, MagicMock
from fastapi import HTTPException
from datetime import datetime
import uuid

from db.proveedor_model import Proveedor
from schemas.proveedor_schema import (
    CrearProveedorSchema,
    ActualizarProveedorSchema,
    PaisEnum,
    TipoProveedorEnum
)


def get_service(mock_db):
    """Helper function to get service instance"""
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
    
    def test_crear_proveedor_exitoso(self, mock_db, valid_proveedor_data, mock_proveedor):
        """Test: Crear un proveedor exitosamente"""
        # Arrange
        proveedor_service = get_service(mock_db)
        mock_db.first.return_value = None  # No existe proveedor duplicado
        
        # Act
        result = proveedor_service.crear_proveedor(valid_proveedor_data)
        
        # Assert
        assert mock_db.add.called
        assert mock_db.commit.called
        assert "nombre" in result
        
    def test_crear_proveedor_id_tributario_duplicado(self, mock_db, valid_proveedor_data, mock_proveedor):
        """Test: Error al crear proveedor con ID tributario duplicado"""
        # Arrange
        proveedor_service = get_service(mock_db)
        mock_db.first.return_value = mock_proveedor  # Ya existe
        
        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            proveedor_service.crear_proveedor(valid_proveedor_data)
        
        assert exc_info.value.status_code == 409
        assert "ID tributario" in exc_info.value.detail
        
    def test_crear_proveedor_email_duplicado(self, mock_db, valid_proveedor_data, mock_proveedor):
        """Test: Error al crear proveedor con email duplicado"""
        # Arrange
        proveedor_service = get_service(mock_db)
        # Primera llamada (id_tributario) retorna None, segunda (email) retorna proveedor
        mock_db.first.side_effect = [None, mock_proveedor]
        
        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            proveedor_service.crear_proveedor(valid_proveedor_data)
        
        assert exc_info.value.status_code == 409
        assert "email" in exc_info.value.detail.lower()


class TestObtenerProveedor:
    """Tests para obtener un proveedor"""
    
    def test_obtener_proveedor_existente(self, mock_db, mock_proveedor):
        """Test: Obtener un proveedor que existe"""
        # Arrange
        proveedor_service = get_service(mock_db)
        proveedor_id = str(uuid.uuid4())
        mock_db.first.return_value = mock_proveedor
        
        # Act
        result = proveedor_service.obtener_proveedor(proveedor_id)
        
        # Assert
        assert result is not None
        assert "nombre" in result
        
    def test_obtener_proveedor_no_existente(self, mock_db):
        """Test: Error al obtener un proveedor que no existe"""
        # Arrange
        proveedor_service = get_service(mock_db)
        proveedor_id = str(uuid.uuid4())
        mock_db.first.return_value = None
        
        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            proveedor_service.obtener_proveedor(proveedor_id)
        
        assert exc_info.value.status_code == 404


class TestListarProveedores:
    """Tests para listar proveedores"""
    
    def test_listar_proveedores_sin_filtros(self, mock_db, mock_proveedor):
        """Test: Listar todos los proveedores sin filtros"""
        # Arrange
        proveedor_service = get_service(mock_db)
        mock_db.all.return_value = [mock_proveedor, mock_proveedor]
        
        # Act
        result = proveedor_service.listar_proveedores()
        
        # Assert
        assert isinstance(result, list)
        assert len(result) == 2
        
    def test_listar_proveedores_con_filtro_pais(self, mock_db, mock_proveedor):
        """Test: Listar proveedores filtrados por país"""
        # Arrange
        proveedor_service = get_service(mock_db)
        mock_db.all.return_value = [mock_proveedor]
        
        # Act
        result = proveedor_service.listar_proveedores(pais="Perú")
        
        # Assert
        assert mock_db.filter.called
        assert len(result) == 1
        
    def test_listar_proveedores_con_paginacion(self, mock_db, mock_proveedor):
        """Test: Listar proveedores con paginación"""
        # Arrange
        proveedor_service = get_service(mock_db)
        mock_db.all.return_value = [mock_proveedor]
        
        # Act
        result = proveedor_service.listar_proveedores(skip=10, limit=5)
        
        # Assert
        assert mock_db.offset.called
        assert mock_db.limit.called


class TestActualizarProveedor:
    """Tests para actualizar proveedores"""
    
    def test_actualizar_proveedor_exitoso(self, mock_db, mock_proveedor):
        """Test: Actualizar un proveedor exitosamente"""
        # Arrange
        proveedor_service = get_service(mock_db)
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
        
    def test_actualizar_proveedor_no_existente(self, mock_db):
        """Test: Error al actualizar un proveedor que no existe"""
        # Arrange
        proveedor_service = get_service(mock_db)
        proveedor_id = str(uuid.uuid4())
        mock_db.first.return_value = None
        update_data = ActualizarProveedorSchema(nombre="Nuevo Nombre")
        
        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            proveedor_service.actualizar_proveedor(proveedor_id, update_data)
        
        assert exc_info.value.status_code == 404
        
    def test_actualizar_proveedor_email_duplicado(self, mock_db, mock_proveedor):
        """Test: Error al actualizar con email que ya existe"""
        # Arrange
        proveedor_service = get_service(mock_db)
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
    
    def test_eliminar_proveedor_exitoso(self, mock_db, mock_proveedor):
        """Test: Eliminar un proveedor exitosamente"""
        # Arrange
        proveedor_service = get_service(mock_db)
        proveedor_id = str(uuid.uuid4())
        mock_db.first.return_value = mock_proveedor
        
        # Act
        result = proveedor_service.eliminar_proveedor(proveedor_id)
        
        # Assert
        assert mock_db.delete.called
        assert mock_db.commit.called
        assert "message" in result
        
    def test_eliminar_proveedor_no_existente(self, mock_db):
        """Test: Error al eliminar un proveedor que no existe"""
        # Arrange
        proveedor_service = get_service(mock_db)
        proveedor_id = str(uuid.uuid4())
        mock_db.first.return_value = None
        
        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            proveedor_service.eliminar_proveedor(proveedor_id)
        
        assert exc_info.value.status_code == 404


class TestContarProveedores:
    """Tests para contar proveedores"""
    
    def test_contar_proveedores_sin_filtros(self, mock_db):
        """Test: Contar todos los proveedores"""
        # Arrange
        proveedor_service = get_service(mock_db)
        mock_db.count.return_value = 10
        
        # Act
        result = proveedor_service.contar_proveedores()
        
        # Assert
        assert result == 10
        
    def test_contar_proveedores_con_filtros(self, mock_db):
        """Test: Contar proveedores con filtros"""
        # Arrange
        proveedor_service = get_service(mock_db)
        mock_db.count.return_value = 5
        
        # Act
        result = proveedor_service.contar_proveedores(pais="Perú", tipo_proveedor="Fabricante")
        
        # Assert
        assert mock_db.filter.called
        assert result == 5

