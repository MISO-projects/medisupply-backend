import os

# Establecer variable de entorno ANTES de cualquier otra importación
os.environ["TESTING"] = "1"

import sys
from pathlib import Path
import pytest
from types import SimpleNamespace
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from unittest.mock import MagicMock, patch

_PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))


@pytest.fixture(autouse=True)
def _set_testing_env(monkeypatch):
    monkeypatch.setenv("TESTING", "1")
    yield


@pytest.fixture(scope="session", autouse=True)
def create_test_database():
    """Crea las tablas de base de datos para los tests"""
    # Este fixture ya no necesita crear tablas porque cada archivo de test
    # maneja su propia base de datos
    yield


@pytest.fixture(autouse=True)
def mock_redis():
    """Mockea la conexión a Redis para todos los tests"""
    mock_redis_client = MagicMock()
    mock_redis_client.ping.return_value = True
    mock_redis_client.get.return_value = None
    mock_redis_client.setex.return_value = True
    mock_redis_client.delete.return_value = True
    
    with patch('db.redis_client.RedisClient') as MockRedisClass:
        mock_instance = MagicMock()
        mock_instance.client = mock_redis_client
        MockRedisClass.return_value = mock_instance
        yield mock_redis_client


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



