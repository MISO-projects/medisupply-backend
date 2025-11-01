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

from services.visita_service import VisitaService, get_visita_service
from services.health_service import HealthService, get_health_service
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
def mock_visita_service() -> Mock:
    """Mock del VisitaService (para pruebas de router)"""
    mock = Mock(spec=VisitaService)
    
    mock.crear_ruta_visita = AsyncMock()
    mock.get_rutas_por_fecha_y_vendedor = AsyncMock()
    mock.get_visita_detalle_por_id = AsyncMock()
    mock.actualizar_visita = AsyncMock()
    return mock

@pytest.fixture(scope="function")
def mock_health_service() -> Mock:
    """Mock del HealthService (para pruebas de router)"""
    return Mock(spec=HealthService)

@pytest.fixture(scope="function")
def client(
    mock_visita_service: Mock,
    mock_health_service: Mock
) -> Generator[TestClient, None, None]:
    """
    Fixture principal de TestClient.
    Importa la app y sobrescribe TODAS sus dependencias.
    """
    
    from main import app 
    
    app.dependency_overrides[get_visita_service] = lambda: mock_visita_service
    app.dependency_overrides[get_health_service] = lambda: mock_health_service
    app.dependency_overrides[get_db] = lambda: Mock(spec=Session) 
    
    with TestClient(app) as c:
        yield c
    

    del app.dependency_overrides[get_visita_service]
    del app.dependency_overrides[get_health_service]
    del app.dependency_overrides[get_db]


@pytest.fixture(scope="function")
def cliente_id_1() -> str:
    return str(uuid4())
@pytest.fixture(scope="function")
def vendedor_id_1() -> str:
    return str(uuid4())