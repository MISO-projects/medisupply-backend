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
TEST_DATABASE_URL = "sqlite:///./test_conductor_router.db"
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
    yield
    # Limpiar la base de datos después de cada test
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def conductor_payload_valido():
    return {
        "nombre": "Juan",
        "apellido": "Pérez",
        "documento": "1234567890",
        "telefono": "3001234567",
        "email": "juan.perez@test.com",
        "licencia_conducir": "C2-12345678",
        "activo": True
    }


class TestConductorRouter:

    def test_crear_conductor_exitosamente(self, conductor_payload_valido):
        # Act
        response = client.post("/api/conductores/", json=conductor_payload_valido)
        
        # Assert
        assert response.status_code == 201
        data = response.json()
        assert "id" in data
        assert data["id"] > 0
        assert data["nombre"] == conductor_payload_valido["nombre"]
        assert data["apellido"] == conductor_payload_valido["apellido"]
        assert data["documento"] == conductor_payload_valido["documento"]
    
    def test_crear_conductor_sin_campos_requeridos(self):
        # Arrange - Payload incompleto
        payload = {
            "nombre": "Juan",
            "apellido": "Pérez"
            # Faltan campos requeridos
        }
        
        # Act
        response = client.post("/api/conductores/", json=payload)
        
        # Assert
        assert response.status_code == 422  # Validation error
    
    def test_crear_conductor_documento_duplicado(self, conductor_payload_valido):
        # Arrange - Crear primer conductor
        client.post("/api/conductores/", json=conductor_payload_valido)
        
        # Act - Intentar crear conductor con mismo documento
        response = client.post("/api/conductores/", json=conductor_payload_valido)
        
        # Assert
        assert response.status_code == 400
        assert "documento" in response.json()["detail"].lower()
    
    def test_crear_conductor_sin_campos_opcionales(self):
        # Arrange
        payload = {
            "nombre": "Pedro",
            "apellido": "González",
            "documento": "5555555555",
            "licencia_conducir": "C2-55555555"
        }
        
        # Act
        response = client.post("/api/conductores/", json=payload)
        
        # Assert
        assert response.status_code == 201
        data = response.json()
        assert data["telefono"] is None
        assert data["email"] is None
        assert data["activo"] is True
    
    def test_obtener_conductor_existente(self, conductor_payload_valido):
        # Arrange - Crear conductor
        response_crear = client.post("/api/conductores/", json=conductor_payload_valido)
        conductor_id = response_crear.json()["id"]
        
        # Act
        response = client.get(f"/api/conductores/{conductor_id}")
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == conductor_id
        assert data["nombre"] == conductor_payload_valido["nombre"]
        assert data["documento"] == conductor_payload_valido["documento"]
        assert "nombre_completo" in data
    
    def test_obtener_conductor_inexistente(self):
        # Act
        response = client.get("/api/conductores/999")
        
        # Assert
        assert response.status_code == 404
    
    def test_listar_conductores_vacia(self):
        # Act
        response = client.get("/api/conductores/")
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, dict)
        assert "conductores" in data
        assert data["total"] == 0
        assert len(data["conductores"]) == 0
    
    def test_listar_conductores_con_datos(self, conductor_payload_valido):
        # Arrange - Crear dos conductores
        client.post("/api/conductores/", json=conductor_payload_valido)
        
        conductor_payload_2 = conductor_payload_valido.copy()
        conductor_payload_2["documento"] = "0987654321"
        conductor_payload_2["nombre"] = "María"
        client.post("/api/conductores/", json=conductor_payload_2)
        
        # Act
        response = client.get("/api/conductores/")
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 2
        assert len(data["conductores"]) == 2
    
    def test_listar_conductores_con_paginacion(self, conductor_payload_valido):
        # Arrange - Crear 3 conductores
        for i in range(3):
            payload = conductor_payload_valido.copy()
            payload["documento"] = f"123456789{i}"
            payload["nombre"] = f"Conductor{i}"
            client.post("/api/conductores/", json=payload)
        
        # Act
        response = client.get("/api/conductores/?page=1&page_size=2")
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 3
        assert len(data["conductores"]) == 2
        assert data["page"] == 1
        assert data["page_size"] == 2
    
    def test_listar_conductores_filtro_activo(self, conductor_payload_valido):
        # Arrange - Crear conductor activo
        client.post("/api/conductores/", json=conductor_payload_valido)
        
        # Crear conductor inactivo
        conductor_payload_2 = conductor_payload_valido.copy()
        conductor_payload_2["documento"] = "0987654321"
        conductor_payload_2["activo"] = False
        client.post("/api/conductores/", json=conductor_payload_2)
        
        # Act - Filtrar solo activos
        response = client.get("/api/conductores/?activo=true")
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert data["conductores"][0]["activo"] is True
    
    def test_actualizar_conductor_existente(self, conductor_payload_valido):
        # Arrange - Crear conductor
        response_crear = client.post("/api/conductores/", json=conductor_payload_valido)
        conductor_id = response_crear.json()["id"]
        
        # Act
        update_payload = {
            "telefono": "3109876543",
            "email": "juan.nuevo@test.com"
        }
        response = client.put(f"/api/conductores/{conductor_id}", json=update_payload)
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["telefono"] == "3109876543"
        assert data["email"] == "juan.nuevo@test.com"
        assert data["nombre"] == conductor_payload_valido["nombre"]  # No cambia
    
    def test_actualizar_conductor_inexistente(self):
        # Arrange
        update_payload = {
            "telefono": "3109876543"
        }
        
        # Act
        response = client.put("/api/conductores/999", json=update_payload)
        
        # Assert
        assert response.status_code == 404
    
    def test_actualizar_conductor_documento_duplicado(self, conductor_payload_valido):
        # Arrange - Crear dos conductores
        response1 = client.post("/api/conductores/", json=conductor_payload_valido)
        conductor1_id = response1.json()["id"]
        
        conductor_payload_2 = conductor_payload_valido.copy()
        conductor_payload_2["documento"] = "0987654321"
        response2 = client.post("/api/conductores/", json=conductor_payload_2)
        conductor2_id = response2.json()["id"]
        
        # Act - Intentar actualizar conductor2 con documento de conductor1
        update_payload = {"documento": conductor_payload_valido["documento"]}
        response = client.put(f"/api/conductores/{conductor2_id}", json=update_payload)
        
        # Assert
        assert response.status_code == 400
        assert "documento" in response.json()["detail"].lower()
    
    def test_eliminar_conductor_existente(self, conductor_payload_valido):
        # Arrange - Crear conductor
        response_crear = client.post("/api/conductores/", json=conductor_payload_valido)
        conductor_id = response_crear.json()["id"]
        
        # Act
        response = client.delete(f"/api/conductores/{conductor_id}")
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        assert "desactivado" in data["mensaje"].lower()
        
        # Verificar que el conductor está desactivado
        response_get = client.get(f"/api/conductores/{conductor_id}")
        assert response_get.json()["activo"] is False
    
    def test_eliminar_conductor_inexistente(self):
        # Act
        response = client.delete("/api/conductores/999")
        
        # Assert
        assert response.status_code == 404

