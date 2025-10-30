import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from db.database import Base
from models.ruta_model import Conductor
from services.conductor_service import ConductorService
from schemas.conductor_schema import ConductorCreateRequest, ConductorUpdateRequest
from fastapi import HTTPException


TEST_DATABASE_URL = "sqlite:///./test_conductor_service.db"
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
def conductor_service(db_session):
    return ConductorService(db=db_session)


@pytest.fixture
def conductor_data_valido():
    return ConductorCreateRequest(
        nombre="Juan",
        apellido="Pérez",
        documento="1234567890",
        telefono="3001234567",
        email="juan.perez@test.com",
        licencia_conducir="C2-12345678",
        activo=True
    )


class TestConductorService:

    def test_crear_conductor_exitosamente(self, conductor_service, conductor_data_valido):
        # Act
        resultado = conductor_service.crear_conductor(conductor_data_valido)
        
        # Assert
        assert resultado.id is not None
        assert resultado.id > 0
        assert resultado.nombre == conductor_data_valido.nombre
        assert resultado.apellido == conductor_data_valido.apellido
        assert resultado.documento == conductor_data_valido.documento
        assert resultado.licencia_conducir == conductor_data_valido.licencia_conducir
        assert resultado.activo is True
    
    def test_crear_conductor_persiste_datos(self, conductor_service, conductor_data_valido, db_session):
        # Act
        resultado = conductor_service.crear_conductor(conductor_data_valido)
        
        # Verificar en la base de datos
        conductor_db = db_session.query(Conductor).filter(Conductor.id == resultado.id).first()
        
        # Assert
        assert conductor_db is not None
        assert conductor_db.nombre == conductor_data_valido.nombre
        assert conductor_db.apellido == conductor_data_valido.apellido
        assert conductor_db.documento == conductor_data_valido.documento
        assert conductor_db.telefono == conductor_data_valido.telefono
        assert conductor_db.email == conductor_data_valido.email
        assert conductor_db.licencia_conducir == conductor_data_valido.licencia_conducir
    
    def test_crear_conductor_documento_duplicado(self, conductor_service, conductor_data_valido):
        # Arrange - Crear primer conductor
        conductor_service.crear_conductor(conductor_data_valido)
        
        # Act & Assert - Intentar crear conductor con mismo documento
        with pytest.raises(HTTPException) as exc_info:
            conductor_service.crear_conductor(conductor_data_valido)
        
        assert exc_info.value.status_code == 400
        assert "documento" in str(exc_info.value.detail).lower()
    
    def test_obtener_conductor_existente(self, conductor_service, conductor_data_valido):
        # Arrange
        conductor_creado = conductor_service.crear_conductor(conductor_data_valido)
        
        # Act
        conductor = conductor_service.obtener_conductor(conductor_creado.id)
        
        # Assert
        assert conductor.id == conductor_creado.id
        assert conductor.nombre == conductor_data_valido.nombre
        assert conductor.apellido == conductor_data_valido.apellido
        assert conductor.documento == conductor_data_valido.documento
    
    def test_obtener_conductor_inexistente(self, conductor_service):
        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            conductor_service.obtener_conductor(999)
        
        assert exc_info.value.status_code == 404
        assert "no encontrado" in str(exc_info.value.detail).lower()
    
    def test_listar_conductores_vacio(self, conductor_service):
        # Act
        resultado = conductor_service.listar_conductores()
        
        # Assert
        assert resultado.total == 0
        assert len(resultado.conductores) == 0
    
    def test_listar_conductores(self, conductor_service, conductor_data_valido):
        # Arrange
        conductor_service.crear_conductor(conductor_data_valido)
        
        conductor_data_2 = conductor_data_valido.model_copy()
        conductor_data_2.documento = "0987654321"
        conductor_data_2.nombre = "María"
        conductor_service.crear_conductor(conductor_data_2)
        
        # Act
        resultado = conductor_service.listar_conductores()
        
        # Assert
        assert resultado.total == 2
        assert len(resultado.conductores) == 2
    
    def test_listar_conductores_con_paginacion(self, conductor_service, conductor_data_valido):
        # Arrange - Crear 3 conductores
        for i in range(3):
            conductor_data = conductor_data_valido.model_copy()
            conductor_data.documento = f"123456789{i}"
            conductor_data.nombre = f"Conductor{i}"
            conductor_service.crear_conductor(conductor_data)
        
        # Act
        resultado = conductor_service.listar_conductores(page=1, page_size=2)
        
        # Assert
        assert resultado.total == 3
        assert len(resultado.conductores) == 2
        assert resultado.page == 1
        assert resultado.page_size == 2
        assert resultado.total_pages == 2
    
    def test_listar_conductores_filtro_activo(self, conductor_service, conductor_data_valido):
        # Arrange - Crear conductor activo
        conductor_service.crear_conductor(conductor_data_valido)
        
        # Crear conductor inactivo
        conductor_data_2 = conductor_data_valido.model_copy()
        conductor_data_2.documento = "0987654321"
        conductor_data_2.activo = False
        conductor_service.crear_conductor(conductor_data_2)
        
        # Act - Filtrar solo activos
        resultado = conductor_service.listar_conductores(activo=True)
        
        # Assert
        assert resultado.total == 1
        assert len(resultado.conductores) == 1
        assert resultado.conductores[0].activo is True
    
    def test_actualizar_conductor_existente(self, conductor_service, conductor_data_valido):
        # Arrange
        conductor_creado = conductor_service.crear_conductor(conductor_data_valido)
        
        # Act
        update_data = ConductorUpdateRequest(
            telefono="3109876543",
            email="juan.nuevo@test.com"
        )
        conductor_actualizado = conductor_service.actualizar_conductor(conductor_creado.id, update_data)
        
        # Assert
        assert conductor_actualizado.id == conductor_creado.id
        assert conductor_actualizado.telefono == "3109876543"
        assert conductor_actualizado.email == "juan.nuevo@test.com"
        assert conductor_actualizado.nombre == conductor_data_valido.nombre  # No cambia
    
    def test_actualizar_conductor_inexistente(self, conductor_service):
        # Act & Assert
        update_data = ConductorUpdateRequest(telefono="3109876543")
        
        with pytest.raises(HTTPException) as exc_info:
            conductor_service.actualizar_conductor(999, update_data)
        
        assert exc_info.value.status_code == 404
    
    def test_actualizar_conductor_documento_duplicado(self, conductor_service, conductor_data_valido):
        # Arrange - Crear dos conductores
        conductor1 = conductor_service.crear_conductor(conductor_data_valido)
        
        conductor_data_2 = conductor_data_valido.model_copy()
        conductor_data_2.documento = "0987654321"
        conductor2 = conductor_service.crear_conductor(conductor_data_2)
        
        # Act & Assert - Intentar actualizar conductor2 con documento de conductor1
        update_data = ConductorUpdateRequest(documento=conductor1.documento)
        
        with pytest.raises(HTTPException) as exc_info:
            conductor_service.actualizar_conductor(conductor2.id, update_data)
        
        assert exc_info.value.status_code == 400
        assert "documento" in str(exc_info.value.detail).lower()
    
    def test_eliminar_conductor_existente(self, conductor_service, conductor_data_valido, db_session):
        # Arrange
        conductor_creado = conductor_service.crear_conductor(conductor_data_valido)
        
        # Act
        resultado = conductor_service.eliminar_conductor(conductor_creado.id)
        
        # Assert
        assert "desactivado" in resultado["mensaje"].lower()
        
        # Verificar que el conductor está desactivado
        conductor_db = db_session.query(Conductor).filter(Conductor.id == conductor_creado.id).first()
        assert conductor_db.activo is False
    
    def test_eliminar_conductor_inexistente(self, conductor_service):
        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            conductor_service.eliminar_conductor(999)
        
        assert exc_info.value.status_code == 404
    
    def test_crear_conductor_sin_campos_opcionales(self, conductor_service):
        # Arrange
        conductor_data = ConductorCreateRequest(
            nombre="Pedro",
            apellido="González",
            documento="5555555555",
            licencia_conducir="C2-55555555"
        )
        
        # Act
        resultado = conductor_service.crear_conductor(conductor_data)
        
        # Assert
        assert resultado.id is not None
        assert resultado.telefono is None
        assert resultado.email is None
        assert resultado.activo is True  # Valor por defecto
    
    def test_nombre_completo_en_respuesta(self, conductor_service, conductor_data_valido):
        # Act
        resultado = conductor_service.crear_conductor(conductor_data_valido)
        
        # Assert
        assert resultado.nombre_completo == f"{conductor_data_valido.nombre} {conductor_data_valido.apellido}"

