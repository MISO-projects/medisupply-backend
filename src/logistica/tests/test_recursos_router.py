import pytest
import os
import sys
from pathlib import Path

# Establecer variable de entorno para usar SQLite en tests
os.environ["TESTING"] = "1"

# Asegurar que el path del proyecto esté en sys.path
_PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from db.database import get_db, Base
from main import app

# Importar modelos DESPUÉS de establecer TESTING para que se registren con Base
from models.ruta_model import Conductor, Vehiculo, Ruta, Parada

# Configuración de base de datos de prueba
TEST_DATABASE_URL = "sqlite:///./test_recursos_router.db"
engine = create_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db

client = TestClient(app)


@pytest.fixture(scope="module", autouse=True)
def setup_module():
    """Setup que se ejecuta una vez por módulo"""
    app.dependency_overrides[get_db] = override_get_db
    yield
    # Limpiar dependency overrides al final del módulo
    app.dependency_overrides.clear()


@pytest.fixture(scope="function", autouse=True)
def setup_database():
    # Crear todas las tablas de base de datos en el engine de test
    Base.metadata.create_all(bind=engine)
    
    # Crear datos de prueba
    db = TestingSessionLocal()
    try:
        # Crear conductores de prueba
        db.execute(
            Conductor.__table__.insert(),
            {
                "id": 1,
                "nombre": "Juan",
                "apellido": "Pérez",
                "documento": "1234567890",
                "telefono": "3001234567",
                "email": "juan.perez@test.com",
                "licencia_conducir": "C2-12345678",
                "activo": True
            }
        )
        
        db.execute(
            Conductor.__table__.insert(),
            {
                "id": 2,
                "nombre": "María",
                "apellido": "González",
                "documento": "0987654321",
                "telefono": "3109876543",
                "email": "maria.gonzalez@test.com",
                "licencia_conducir": "C2-87654321",
                "activo": False
            }
        )
        
        # Crear vehículos de prueba
        db.execute(
            Vehiculo.__table__.insert(),
            {
                "id": 1,
                "placa": "ABC123",
                "marca": "Chevrolet",
                "modelo": "NQR",
                "año": 2022,
                "tipo": "Camión refrigerado",
                "capacidad_kg": 3500,
                "activo": True
            }
        )
        
        db.execute(
            Vehiculo.__table__.insert(),
            {
                "id": 2,
                "placa": "XYZ789",
                "marca": "Toyota",
                "modelo": "Hilux",
                "año": 2021,
                "tipo": "Camioneta",
                "capacidad_kg": 1000,
                "activo": False
            }
        )
        
        db.commit()
    finally:
        db.close()
    
    yield
    # Limpiar la base de datos después de cada test
    Base.metadata.drop_all(bind=engine)


class TestRecursosRouter:

    def test_listar_conductores_todos(self):
        # Act
        response = client.get("/api/recursos/conductores")
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 2
        assert data[0]["nombre"] == "Juan"
        assert data[1]["nombre"] == "María"
    
    def test_listar_conductores_filtro_activo(self):
        # Act
        response = client.get("/api/recursos/conductores?activo=true")
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 1
        assert data[0]["nombre"] == "Juan"
        assert data[0]["activo"] is True
    
    def test_listar_conductores_filtro_inactivo(self):
        # Act
        response = client.get("/api/recursos/conductores?activo=false")
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 1
        assert data[0]["nombre"] == "María"
        assert data[0]["activo"] is False
    
    def test_obtener_conductor_existente(self):
        # Act
        response = client.get("/api/recursos/conductores/1")
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == 1
        assert data["nombre"] == "Juan"
        assert data["apellido"] == "Pérez"
        assert "nombre_completo" in data
    
    def test_obtener_conductor_inexistente(self):
        # Act
        response = client.get("/api/recursos/conductores/999")
        
        # Assert
        assert response.status_code == 404
    
    def test_listar_vehiculos_todos(self):
        # Act
        response = client.get("/api/recursos/vehiculos")
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 2
        assert data[0]["placa"] == "ABC123"
        assert data[1]["placa"] == "XYZ789"
    
    def test_listar_vehiculos_filtro_activo(self):
        # Act
        response = client.get("/api/recursos/vehiculos?activo=true")
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 1
        assert data[0]["placa"] == "ABC123"
        assert data[0]["activo"] is True
    
    def test_listar_vehiculos_filtro_inactivo(self):
        # Act
        response = client.get("/api/recursos/vehiculos?activo=false")
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 1
        assert data[0]["placa"] == "XYZ789"
        assert data[0]["activo"] is False
    
    def test_listar_vehiculos_filtro_tipo(self):
        # Act
        response = client.get("/api/recursos/vehiculos?tipo=Camioneta")
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 1
        assert data[0]["tipo"] == "Camioneta"
    
    def test_listar_vehiculos_filtro_tipo_y_activo(self):
        # Act
        response = client.get("/api/recursos/vehiculos?tipo=Camión refrigerado&activo=true")
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 1
        assert data[0]["tipo"] == "Camión refrigerado"
        assert data[0]["activo"] is True
    
    def test_obtener_vehiculo_existente(self):
        # Act
        response = client.get("/api/recursos/vehiculos/1")
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == 1
        assert data["placa"] == "ABC123"
        assert data["marca"] == "Chevrolet"
    
    def test_obtener_vehiculo_inexistente(self):
        # Act
        response = client.get("/api/recursos/vehiculos/999")
        
        # Assert
        assert response.status_code == 404
    
    def test_conductor_response_tiene_nombre_completo(self):
        # Act
        response = client.get("/api/recursos/conductores")
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        assert len(data) > 0
        assert "nombre_completo" in data[0]
        assert data[0]["nombre_completo"] == "Juan Pérez"

