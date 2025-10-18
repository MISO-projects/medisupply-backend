import os
import sys
from pathlib import Path
import pytest
from types import SimpleNamespace
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient
from uuid import uuid4

_PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))


@pytest.fixture(autouse=True)
def _set_testing_env(monkeypatch):
    monkeypatch.setenv("TESTING", "1")
    yield


class FakeDB:
    def __init__(self, should_fail: bool = False):
        self.should_fail = should_fail

    def execute(self, *_args, **_kwargs):
        if self.should_fail:
            raise RuntimeError("DB error")
        return SimpleNamespace()


class FakeRedisClient:
    def __init__(self, should_fail: bool = False, connected: bool = True):
        self.should_fail = should_fail
        self.connected = connected

    @property
    def client(self):
        if self.should_fail:
            raise RuntimeError("Redis error")

        class _Client:
            def __init__(self, connected: bool):
                self._connected = connected

            def ping(self):
                return self._connected

        return _Client(self.connected)


@pytest.fixture
def healthy_deps():
    return {
        "db": FakeDB(should_fail=False),
        "redis_client": FakeRedisClient(should_fail=False, connected=True),
    }


@pytest.fixture
def failing_db_deps():
    return {
        "db": FakeDB(should_fail=True),
        "redis_client": FakeRedisClient(should_fail=False, connected=True),
    }


@pytest.fixture
def failing_cache_deps():
    return {
        "db": FakeDB(should_fail=False),
        "redis_client": FakeRedisClient(should_fail=False, connected=False),
    }


# Fixtures para tests de productos
SQLALCHEMY_DATABASE_URL = "sqlite:///./test_productos.db"

@pytest.fixture(scope="function")
def test_db():
    """Crea una base de datos de prueba en memoria"""
    from db.database import Base
    # Import models to ensure they're registered with Base
    from models.producto import Producto
    
    engine = create_engine(
        SQLALCHEMY_DATABASE_URL,
        connect_args={"check_same_thread": False}
    )
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    
    # Crear las tablas
    Base.metadata.create_all(bind=engine)
    
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        # Limpiar la base de datos después de cada test
        Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def client(test_db, monkeypatch):
    """Cliente de prueba de FastAPI con la base de datos de test"""
    from main import app
    from db.database import get_db
    from unittest.mock import AsyncMock, patch
    import httpx
    
    def override_get_db():
        try:
            yield test_db
        finally:
            pass
    
    # Mock the httpx client for provider verification
    async def mock_httpx_get(*args, **kwargs):
        class MockResponse:
            status_code = 200
            def json(self):
                return {"data": {"id": str(uuid4()), "nombre": "Proveedor Test"}}
        return MockResponse()
    
    app.dependency_overrides[get_db] = override_get_db
    
    with patch('httpx.AsyncClient') as mock_client:
        mock_client.return_value.__aenter__.return_value.get = AsyncMock(side_effect=mock_httpx_get)
        with TestClient(app) as test_client:
            yield test_client
    
    app.dependency_overrides.clear()


@pytest.fixture
def producto_ejemplo():
    """Producto de ejemplo para tests"""
    return {
        "nombre": "Paracetamol 500mg Test",
        "descripcion": "Analgésico de prueba",
        "categoria": "MEDICAMENTOS",
        "imagen_url": "https://example.com/test.jpg",
        "precio_unitario": 15.50,
        "stock_disponible": 100,
        "disponible": True,
        "unidad_medida": "CAJA",
        "sku": "TEST-PAR-500",
        "tipo_almacenamiento": "AMBIENTE",
        "observaciones": "Producto de prueba",
        "proveedor_id": str(uuid4())
    }


@pytest.fixture
def proveedor_id():
    """ID de proveedor para tests"""
    return uuid4()



