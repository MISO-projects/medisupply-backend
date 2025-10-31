import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from db.database import Base
from models.ruta_model import Vehiculo
from services.vehiculo_service import VehiculoService
from schemas.vehiculo_schema import VehiculoCreateRequest, VehiculoUpdateRequest
from fastapi import HTTPException


TEST_DATABASE_URL = "sqlite:///./test_vehiculo_service.db"
engine = create_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(scope="function")
def db_session():
    Base.metadata.create_all(bind=engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture
def vehiculo_service(db_session):
    return VehiculoService(db=db_session)


@pytest.fixture
def vehiculo_data_valido():
    return VehiculoCreateRequest(
        placa="ABC123",
        marca="Chevrolet",
        modelo="NQR",
        año=2022,
        tipo="Camión refrigerado",
        capacidad_kg=3500,
        activo=True
    )


class TestVehiculoService:

    def test_crear_vehiculo_exitosamente(self, vehiculo_service, vehiculo_data_valido):
        # Act
        resultado = vehiculo_service.crear_vehiculo(vehiculo_data_valido)
        
        # Assert
        assert resultado.id is not None
        assert resultado.id > 0
        assert resultado.placa == vehiculo_data_valido.placa
        assert resultado.marca == vehiculo_data_valido.marca
        assert resultado.modelo == vehiculo_data_valido.modelo
        assert resultado.tipo == vehiculo_data_valido.tipo
        assert resultado.activo is True
    
    def test_crear_vehiculo_persiste_datos(self, vehiculo_service, vehiculo_data_valido, db_session):
        # Act
        resultado = vehiculo_service.crear_vehiculo(vehiculo_data_valido)
        
        # Verificar en la base de datos
        vehiculo_db = db_session.query(Vehiculo).filter(Vehiculo.id == resultado.id).first()
        
        # Assert
        assert vehiculo_db is not None
        assert vehiculo_db.placa == vehiculo_data_valido.placa
        assert vehiculo_db.marca == vehiculo_data_valido.marca
        assert vehiculo_db.modelo == vehiculo_data_valido.modelo
        assert vehiculo_db.año == vehiculo_data_valido.año
        assert vehiculo_db.tipo == vehiculo_data_valido.tipo
        assert vehiculo_db.capacidad_kg == vehiculo_data_valido.capacidad_kg
    
    def test_crear_vehiculo_placa_duplicada(self, vehiculo_service, vehiculo_data_valido):
        # Arrange - Crear primer vehículo
        vehiculo_service.crear_vehiculo(vehiculo_data_valido)
        
        # Act & Assert - Intentar crear vehículo con misma placa
        with pytest.raises(HTTPException) as exc_info:
            vehiculo_service.crear_vehiculo(vehiculo_data_valido)
        
        assert exc_info.value.status_code == 400
        assert "placa" in str(exc_info.value.detail).lower()
    
    def test_obtener_vehiculo_existente(self, vehiculo_service, vehiculo_data_valido):
        # Arrange
        vehiculo_creado = vehiculo_service.crear_vehiculo(vehiculo_data_valido)
        
        # Act
        vehiculo = vehiculo_service.obtener_vehiculo(vehiculo_creado.id)
        
        # Assert
        assert vehiculo.id == vehiculo_creado.id
        assert vehiculo.placa == vehiculo_data_valido.placa
        assert vehiculo.marca == vehiculo_data_valido.marca
        assert vehiculo.modelo == vehiculo_data_valido.modelo
    
    def test_obtener_vehiculo_inexistente(self, vehiculo_service):
        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            vehiculo_service.obtener_vehiculo(999)
        
        assert exc_info.value.status_code == 404
        assert "no encontrado" in str(exc_info.value.detail).lower()
    
    def test_listar_vehiculos_vacio(self, vehiculo_service):
        # Act
        resultado = vehiculo_service.listar_vehiculos()
        
        # Assert
        assert resultado.total == 0
        assert len(resultado.vehiculos) == 0
    
    def test_listar_vehiculos(self, vehiculo_service, vehiculo_data_valido):
        # Arrange
        vehiculo_service.crear_vehiculo(vehiculo_data_valido)
        
        vehiculo_data_2 = vehiculo_data_valido.model_copy()
        vehiculo_data_2.placa = "XYZ789"
        vehiculo_data_2.marca = "Toyota"
        vehiculo_service.crear_vehiculo(vehiculo_data_2)
        
        # Act
        resultado = vehiculo_service.listar_vehiculos()
        
        # Assert
        assert resultado.total == 2
        assert len(resultado.vehiculos) == 2
    
    def test_listar_vehiculos_con_paginacion(self, vehiculo_service, vehiculo_data_valido):
        # Arrange - Crear 3 vehículos
        for i in range(3):
            vehiculo_data = vehiculo_data_valido.model_copy()
            vehiculo_data.placa = f"ABC{i}{i}{i}"
            vehiculo_data.marca = f"Marca{i}"
            vehiculo_service.crear_vehiculo(vehiculo_data)
        
        # Act
        resultado = vehiculo_service.listar_vehiculos(page=1, page_size=2)
        
        # Assert
        assert resultado.total == 3
        assert len(resultado.vehiculos) == 2
        assert resultado.page == 1
        assert resultado.page_size == 2
        assert resultado.total_pages == 2
    
    def test_listar_vehiculos_filtro_activo(self, vehiculo_service, vehiculo_data_valido):
        # Arrange - Crear vehículo activo
        vehiculo_service.crear_vehiculo(vehiculo_data_valido)
        
        # Crear vehículo inactivo
        vehiculo_data_2 = vehiculo_data_valido.model_copy()
        vehiculo_data_2.placa = "XYZ789"
        vehiculo_data_2.activo = False
        vehiculo_service.crear_vehiculo(vehiculo_data_2)
        
        # Act - Filtrar solo activos
        resultado = vehiculo_service.listar_vehiculos(activo=True)
        
        # Assert
        assert resultado.total == 1
        assert len(resultado.vehiculos) == 1
        assert resultado.vehiculos[0].activo is True
    
    def test_actualizar_vehiculo_existente(self, vehiculo_service, vehiculo_data_valido):
        # Arrange
        vehiculo_creado = vehiculo_service.crear_vehiculo(vehiculo_data_valido)
        
        # Act
        update_data = VehiculoUpdateRequest(
            capacidad_kg=4000,
            tipo="Camión de carga"
        )
        vehiculo_actualizado = vehiculo_service.actualizar_vehiculo(vehiculo_creado.id, update_data)
        
        # Assert
        assert vehiculo_actualizado.id == vehiculo_creado.id
        assert vehiculo_actualizado.capacidad_kg == 4000
        assert vehiculo_actualizado.tipo == "Camión de carga"
        assert vehiculo_actualizado.placa == vehiculo_data_valido.placa  # No cambia
    
    def test_actualizar_vehiculo_inexistente(self, vehiculo_service):
        # Act & Assert
        update_data = VehiculoUpdateRequest(capacidad_kg=4000)
        
        with pytest.raises(HTTPException) as exc_info:
            vehiculo_service.actualizar_vehiculo(999, update_data)
        
        assert exc_info.value.status_code == 404
    
    def test_actualizar_vehiculo_placa_duplicada(self, vehiculo_service, vehiculo_data_valido):
        # Arrange - Crear dos vehículos
        vehiculo1 = vehiculo_service.crear_vehiculo(vehiculo_data_valido)
        
        vehiculo_data_2 = vehiculo_data_valido.model_copy()
        vehiculo_data_2.placa = "XYZ789"
        vehiculo2 = vehiculo_service.crear_vehiculo(vehiculo_data_2)
        
        # Act & Assert - Intentar actualizar vehiculo2 con placa de vehiculo1
        update_data = VehiculoUpdateRequest(placa=vehiculo1.placa)
        
        with pytest.raises(HTTPException) as exc_info:
            vehiculo_service.actualizar_vehiculo(vehiculo2.id, update_data)
        
        assert exc_info.value.status_code == 400
        assert "placa" in str(exc_info.value.detail).lower()
    
    def test_eliminar_vehiculo_existente(self, vehiculo_service, vehiculo_data_valido, db_session):
        # Arrange
        vehiculo_creado = vehiculo_service.crear_vehiculo(vehiculo_data_valido)
        
        # Act
        resultado = vehiculo_service.eliminar_vehiculo(vehiculo_creado.id)
        
        # Assert
        assert "desactivado" in resultado["mensaje"].lower()
        
        # Verificar que el vehículo está desactivado
        vehiculo_db = db_session.query(Vehiculo).filter(Vehiculo.id == vehiculo_creado.id).first()
        assert vehiculo_db.activo is False
    
    def test_eliminar_vehiculo_inexistente(self, vehiculo_service):
        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            vehiculo_service.eliminar_vehiculo(999)
        
        assert exc_info.value.status_code == 404
    
    def test_crear_vehiculo_sin_campos_opcionales(self, vehiculo_service):
        # Arrange
        vehiculo_data = VehiculoCreateRequest(
            placa="DEF456",
            marca="Ford",
            modelo="F-150",
            tipo="Camioneta"
        )
        
        # Act
        resultado = vehiculo_service.crear_vehiculo(vehiculo_data)
        
        # Assert
        assert resultado.id is not None
        assert resultado.año is None
        assert resultado.capacidad_kg is None
        assert resultado.activo is True  # Valor por defecto

