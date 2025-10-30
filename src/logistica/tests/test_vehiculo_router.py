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
TEST_DATABASE_URL = "sqlite:///./test_vehiculo_router.db"
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
def vehiculo_payload_valido():
    return {
        "placa": "ABC123",
        "marca": "Chevrolet",
        "modelo": "NQR",
        "año": 2022,
        "tipo": "Camión refrigerado",
        "capacidad_kg": 3500,
        "activo": True
    }


class TestVehiculoRouter:

    def test_crear_vehiculo_exitosamente(self, vehiculo_payload_valido):
        # Act
        response = client.post("/api/vehiculos/", json=vehiculo_payload_valido)
        
        # Assert
        assert response.status_code == 201
        data = response.json()
        assert "id" in data
        assert data["id"] > 0
        assert data["placa"] == vehiculo_payload_valido["placa"]
        assert data["marca"] == vehiculo_payload_valido["marca"]
        assert data["modelo"] == vehiculo_payload_valido["modelo"]
    
    def test_crear_vehiculo_sin_campos_requeridos(self):
        # Arrange - Payload incompleto
        payload = {
            "placa": "ABC123",
            "marca": "Chevrolet"
            # Faltan campos requeridos
        }
        
        # Act
        response = client.post("/api/vehiculos/", json=payload)
        
        # Assert
        assert response.status_code == 422  # Validation error
    
    def test_crear_vehiculo_placa_duplicada(self, vehiculo_payload_valido):
        # Arrange - Crear primer vehículo
        client.post("/api/vehiculos/", json=vehiculo_payload_valido)
        
        # Act - Intentar crear vehículo con misma placa
        response = client.post("/api/vehiculos/", json=vehiculo_payload_valido)
        
        # Assert
        assert response.status_code == 400
        assert "placa" in response.json()["detail"].lower()
    
    def test_crear_vehiculo_sin_campos_opcionales(self):
        # Arrange
        payload = {
            "placa": "DEF456",
            "marca": "Ford",
            "modelo": "F-150",
            "tipo": "Camioneta"
        }
        
        # Act
        response = client.post("/api/vehiculos/", json=payload)
        
        # Assert
        assert response.status_code == 201
        data = response.json()
        assert data["año"] is None
        assert data["capacidad_kg"] is None
        assert data["activo"] is True
    
    def test_obtener_vehiculo_existente(self, vehiculo_payload_valido):
        # Arrange - Crear vehículo
        response_crear = client.post("/api/vehiculos/", json=vehiculo_payload_valido)
        vehiculo_id = response_crear.json()["id"]
        
        # Act
        response = client.get(f"/api/vehiculos/{vehiculo_id}")
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == vehiculo_id
        assert data["placa"] == vehiculo_payload_valido["placa"]
        assert data["marca"] == vehiculo_payload_valido["marca"]
    
    def test_obtener_vehiculo_inexistente(self):
        # Act
        response = client.get("/api/vehiculos/999")
        
        # Assert
        assert response.status_code == 404
    
    def test_listar_vehiculos_vacia(self):
        # Act
        response = client.get("/api/vehiculos/")
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, dict)
        assert "vehiculos" in data
        assert data["total"] == 0
        assert len(data["vehiculos"]) == 0
    
    def test_listar_vehiculos_con_datos(self, vehiculo_payload_valido):
        # Arrange - Crear dos vehículos
        client.post("/api/vehiculos/", json=vehiculo_payload_valido)
        
        vehiculo_payload_2 = vehiculo_payload_valido.copy()
        vehiculo_payload_2["placa"] = "XYZ789"
        vehiculo_payload_2["marca"] = "Toyota"
        client.post("/api/vehiculos/", json=vehiculo_payload_2)
        
        # Act
        response = client.get("/api/vehiculos/")
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 2
        assert len(data["vehiculos"]) == 2
    
    def test_listar_vehiculos_con_paginacion(self, vehiculo_payload_valido):
        # Arrange - Crear 3 vehículos
        for i in range(3):
            payload = vehiculo_payload_valido.copy()
            payload["placa"] = f"ABC{i}{i}{i}"
            payload["marca"] = f"Marca{i}"
            client.post("/api/vehiculos/", json=payload)
        
        # Act
        response = client.get("/api/vehiculos/?page=1&page_size=2")
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 3
        assert len(data["vehiculos"]) == 2
        assert data["page"] == 1
        assert data["page_size"] == 2
    
    def test_listar_vehiculos_filtro_activo(self, vehiculo_payload_valido):
        # Arrange - Crear vehículo activo
        client.post("/api/vehiculos/", json=vehiculo_payload_valido)
        
        # Crear vehículo inactivo
        vehiculo_payload_2 = vehiculo_payload_valido.copy()
        vehiculo_payload_2["placa"] = "XYZ789"
        vehiculo_payload_2["activo"] = False
        client.post("/api/vehiculos/", json=vehiculo_payload_2)
        
        # Act - Filtrar solo activos
        response = client.get("/api/vehiculos/?activo=true")
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert data["vehiculos"][0]["activo"] is True
    
    def test_actualizar_vehiculo_existente(self, vehiculo_payload_valido):
        # Arrange - Crear vehículo
        response_crear = client.post("/api/vehiculos/", json=vehiculo_payload_valido)
        vehiculo_id = response_crear.json()["id"]
        
        # Act
        update_payload = {
            "capacidad_kg": 4000,
            "tipo": "Camión de carga"
        }
        response = client.put(f"/api/vehiculos/{vehiculo_id}", json=update_payload)
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["capacidad_kg"] == 4000
        assert data["tipo"] == "Camión de carga"
        assert data["placa"] == vehiculo_payload_valido["placa"]  # No cambia
    
    def test_actualizar_vehiculo_inexistente(self):
        # Arrange
        update_payload = {
            "capacidad_kg": 4000
        }
        
        # Act
        response = client.put("/api/vehiculos/999", json=update_payload)
        
        # Assert
        assert response.status_code == 404
    
    def test_actualizar_vehiculo_placa_duplicada(self, vehiculo_payload_valido):
        # Arrange - Crear dos vehículos
        response1 = client.post("/api/vehiculos/", json=vehiculo_payload_valido)
        vehiculo1_id = response1.json()["id"]
        
        vehiculo_payload_2 = vehiculo_payload_valido.copy()
        vehiculo_payload_2["placa"] = "XYZ789"
        response2 = client.post("/api/vehiculos/", json=vehiculo_payload_2)
        vehiculo2_id = response2.json()["id"]
        
        # Act - Intentar actualizar vehiculo2 con placa de vehiculo1
        update_payload = {"placa": vehiculo_payload_valido["placa"]}
        response = client.put(f"/api/vehiculos/{vehiculo2_id}", json=update_payload)
        
        # Assert
        assert response.status_code == 400
        assert "placa" in response.json()["detail"].lower()
    
    def test_eliminar_vehiculo_existente(self, vehiculo_payload_valido):
        # Arrange - Crear vehículo
        response_crear = client.post("/api/vehiculos/", json=vehiculo_payload_valido)
        vehiculo_id = response_crear.json()["id"]
        
        # Act
        response = client.delete(f"/api/vehiculos/{vehiculo_id}")
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        assert "desactivado" in data["mensaje"].lower()
        
        # Verificar que el vehículo está desactivado
        response_get = client.get(f"/api/vehiculos/{vehiculo_id}")
        assert response_get.json()["activo"] is False
    
    def test_eliminar_vehiculo_inexistente(self):
        # Act
        response = client.delete("/api/vehiculos/999")
        
        # Assert
        assert response.status_code == 404

