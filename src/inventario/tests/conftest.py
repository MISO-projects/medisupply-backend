import os
import sys
from pathlib import Path
import pytest
from types import SimpleNamespace
from unittest.mock import Mock, AsyncMock
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from uuid import uuid4
from typing import Generator 
_PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

# --- Imports de la App (se importan DESPUÉS de arreglar el path) ---
from services.inventario_service import InventarioService, get_inventario_service
from services.health_service import HealthService, get_health_service
from services.auth_dependency import get_current_user
from db.database import get_db


@pytest.fixture(autouse=True)
def _set_testing_env(monkeypatch):
    """Activa el modo TESTING antes de que se importe la app."""
    monkeypatch.setenv("TESTING", "1")
    yield

class FakeDB:
    def __init__(self, should_fail: bool = False): self.should_fail = should_fail
    def execute(self, *_args, **_kwargs):
        if self.should_fail: raise RuntimeError("DB error")
        return SimpleNamespace()
class FakeRedisClient:
    def __init__(self, should_fail: bool = False, connected: bool = True):
        self.should_fail = should_fail; self.connected = connected
    @property
    def client(self):
        if self.should_fail: raise RuntimeError("Redis error")
        class _Client:
            def __init__(self, connected: bool): self._connected = connected
            def ping(self): return self._connected
        return _Client(self.connected)
@pytest.fixture
def healthy_deps():
    return {"db": FakeDB(), "redis_client": FakeRedisClient()}
@pytest.fixture
def failing_db_deps():
    return {"db": FakeDB(should_fail=True), "redis_client": FakeRedisClient()}
@pytest.fixture
def failing_cache_deps():
    return {"db": FakeDB(), "redis_client": FakeRedisClient(connected=False)}

@pytest.fixture(scope="function")
def mock_db() -> Mock:
    """Mock de una sesión de SQLAlchemy"""
    return Mock(spec=Session)

@pytest.fixture(scope="function")
def mock_inventory_service() -> Mock:
    """Mock del InventarioService (para pruebas de router)"""
    mock = Mock(spec=InventarioService)
    mock.listar_registros_paginados = AsyncMock()
    mock._get_detalles_productos = AsyncMock()
    return mock

@pytest.fixture(scope="function")
def mock_health_service() -> Mock:
    """Mock del HealthService (para pruebas de router)"""
    return Mock(spec=HealthService)

@pytest.fixture(scope="function")
def mock_current_user() -> dict:
    """Mock del usuario autenticado para pruebas"""
    return {
        "sub": str(uuid4()),  # user_id
        "email": "test@example.com",
        "role": "admin"
    }

@pytest.fixture(scope="function")
def client(mock_inventory_service: Mock, mock_health_service: Mock, mock_current_user: dict) -> Generator[TestClient, None, None]:
    """
    Fixture principal de TestClient.
    Importa la app y sobrescribe TODAS sus dependencias.
    """
    
    from main import app 
    
    app.dependency_overrides[get_inventario_service] = lambda: mock_inventory_service
    app.dependency_overrides[get_health_service] = lambda: mock_health_service
    app.dependency_overrides[get_db] = lambda: Mock(spec=Session)
    # Sobrescribir autenticación para tests
    app.dependency_overrides[get_current_user] = lambda: mock_current_user
    
    with TestClient(app) as c:
        yield c
    

    del app.dependency_overrides[get_inventario_service]
    del app.dependency_overrides[get_health_service]
    del app.dependency_overrides[get_db]
    if get_current_user in app.dependency_overrides:
        del app.dependency_overrides[get_current_user]


@pytest.fixture(scope="function")
def producto_id_1() -> str:
    return str(uuid4())
@pytest.fixture(scope="function")
def producto_id_2() -> str:
    return str(uuid4())