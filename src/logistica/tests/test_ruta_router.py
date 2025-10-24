import pytest
import os

# Establecer variable de entorno para usar SQLite en tests
os.environ["TESTING"] = "1"

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from db.database import Base, get_db
from main import app


# Configuración de base de datos de prueba
TEST_DATABASE_URL = "sqlite:///./test_logistica_router.db"
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


@pytest.fixture(scope="function", autouse=True)
def setup_database():
    from models.ruta_model import Conductor, Vehiculo
    
    Base.metadata.create_all(bind=engine)
    
    # Crear datos de prueba
    db = TestingSessionLocal()
    try:
        # Crear conductor de prueba con SQL directo para especificar el ID
        db.execute(
            Conductor.__table__.insert(),
            {
                "id": 4,
                "nombre": "Juan",
                "apellido": "Pérez",
                "documento": "1234567890",
                "telefono": "3001234567",
                "email": "juan.perez@test.com",
                "licencia_conducir": "C2-12345678",
                "activo": True
            }
        )
        
        # Crear vehículo de prueba con SQL directo para especificar el ID
        db.execute(
            Vehiculo.__table__.insert(),
            {
                "id": 12,
                "placa": "ABC123",
                "marca": "Chevrolet",
                "modelo": "NQR",
                "año": 2022,
                "tipo": "Camión refrigerado",
                "capacidad_kg": 3500,
                "activo": True
            }
        )
        
        db.commit()
    finally:
        db.close()
    
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def ruta_payload_valida():
    return {
        "fecha": "2025-08-17",
        "bodega_origen": "Central Bogotá",
        "estado": "Pendiente",
        "vehiculo_id": 12,
        "conductor_id": 4,
        "condiciones_almacenamiento": "Refrigerado",
        "paradas": [
            {
                "cliente_id": 32,
                "direccion": "Calle 80 #45-20",
                "contacto": "Carlos Ríos",
                "latitud": 4.7110,
                "longitud": -74.0721
            },
            {
                "cliente_id": 15,
                "direccion": "Av. 30 #22-10",
                "contacto": "María López",
                "latitud": 4.6097,
                "longitud": -74.0817
            }
        ]
    }


class TestRutaRouter:

    def test_crear_ruta_exitosamente(self, ruta_payload_valida):
        # Act
        response = client.post("/api/rutas/", json=ruta_payload_valida)
        
        # Assert
        assert response.status_code == 201
        data = response.json()
        assert "id" in data
        assert data["id"] > 0
        assert data["mensaje"] == "Ruta creada exitosamente"
    
    def test_crear_ruta_sin_paradas(self):
        # Arrange
        payload = {
            "fecha": "2025-08-17",
            "bodega_origen": "Central Bogotá",
            "estado": "Pendiente",
            "vehiculo_id": 12,
            "conductor_id": 4,
            "paradas": []
        }
        
        # Act
        response = client.post("/api/rutas/", json=payload)
        
        # Assert
        assert response.status_code == 422  # Validation error
    
    def test_crear_ruta_fecha_invalida(self, ruta_payload_valida):
        # Arrange
        ruta_payload_valida["fecha"] = "2025-13-45"  # Fecha inválida
        
        # Act
        response = client.post("/api/rutas/", json=ruta_payload_valida)
        
        # Assert
        assert response.status_code == 422  # Validation error
    
    def test_crear_ruta_vehiculo_id_invalido(self, ruta_payload_valida):
        # Arrange
        ruta_payload_valida["vehiculo_id"] = 0  # ID inválido
        
        # Act
        response = client.post("/api/rutas/", json=ruta_payload_valida)
        
        # Assert
        assert response.status_code == 422  # Validation error
    
    def test_obtener_ruta_existente(self, ruta_payload_valida):
        response_crear = client.post("/api/rutas/", json=ruta_payload_valida)
        ruta_id = response_crear.json()["id"]
        
        # Act
        response = client.get(f"/api/rutas/{ruta_id}")
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == ruta_id
        assert data["fecha"] == ruta_payload_valida["fecha"]
        assert data["bodega_origen"] == ruta_payload_valida["bodega_origen"]
        assert len(data["paradas"]) == 2
    
    def test_obtener_ruta_inexistente(self):
        # Act
        response = client.get("/api/rutas/999")
        
        # Assert
        assert response.status_code == 404
    
    def test_listar_rutas_vacia(self):
        # Act
        response = client.get("/api/rutas/")
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, dict)
        assert "rutas" in data
        assert data["total"] == 0
        assert len(data["rutas"]) == 0
    
    def test_listar_rutas_con_datos(self, ruta_payload_valida):
        client.post("/api/rutas/", json=ruta_payload_valida)
        
        ruta_payload_2 = ruta_payload_valida.copy()
        ruta_payload_2["fecha"] = "2025-08-18"
        client.post("/api/rutas/", json=ruta_payload_2)
        
        # Act
        response = client.get("/api/rutas/")
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 2
        assert len(data["rutas"]) == 2
    
    def test_listar_rutas_con_paginacion(self, ruta_payload_valida):
        for i in range(3):
            payload = ruta_payload_valida.copy()
            payload["fecha"] = f"2025-08-{17+i}"
            client.post("/api/rutas/", json=payload)
        
        # Act
        response = client.get("/api/rutas/?page=1&page_size=2")
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 3
        assert len(data["rutas"]) == 2
        assert data["page"] == 1
        assert data["page_size"] == 2
    
    def test_crear_ruta_con_coordenadas(self, ruta_payload_valida):
        # Act
        response_crear = client.post("/api/rutas/", json=ruta_payload_valida)
        ruta_id = response_crear.json()["id"]
        
        response_obtener = client.get(f"/api/rutas/{ruta_id}")
        
        # Assert
        assert response_obtener.status_code == 200
        data = response_obtener.json()
        paradas = data["paradas"]
        
        assert paradas[0]["latitud"] == 4.7110
        assert paradas[0]["longitud"] == -74.0721
        assert paradas[1]["latitud"] == 4.6097
        assert paradas[1]["longitud"] == -74.0817
    
    def test_crear_ruta_sin_coordenadas_opcional(self):
        # Arrange
        payload = {
            "fecha": "2025-08-17",
            "bodega_origen": "Central Bogotá",
            "estado": "Pendiente",
            "vehiculo_id": 12,
            "conductor_id": 4,
            "paradas": [
                {
                    "cliente_id": 32,
                    "direccion": "Calle 80 #45-20",
                    "contacto": "Carlos Ríos"
                }
            ]
        }
        
        # Act
        response = client.post("/api/rutas/", json=payload)
        
        # Assert
        assert response.status_code == 201
        data = response.json()
        assert data["id"] > 0
    
    def test_crear_ruta_campos_requeridos(self):
        # Arrange - Payload incompleto
        payload = {
            "fecha": "2025-08-17",
            "bodega_origen": "Central Bogotá"
            # Faltan campos requeridos
        }
        
        # Act
        response = client.post("/api/rutas/", json=payload)
        
        # Assert
        assert response.status_code == 422  # Validation error
    
    def test_health_check(self):
        """Test: GET /health - Health check funciona"""
        # Act
        response = client.get("/health")
        
        # Assert
        assert response.status_code in [200, 503]

