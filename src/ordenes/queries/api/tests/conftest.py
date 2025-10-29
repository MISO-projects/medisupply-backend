import os
import sys
from pathlib import Path
import pytest
from types import SimpleNamespace

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


@pytest.fixture
def sample_orders():
    """Sample order data for testing"""
    return [
        {
            "id": "order-1",
            "numero_orden": "ORD-001",
            "id_cliente": "client-123",
            "estado": "PENDING",
            "fecha_creacion": "2024-01-01T10:00:00",
        },
        {
            "id": "order-2",
            "numero_orden": "ORD-002",
            "id_cliente": "client-123",
            "estado": "COMPLETED",
            "fecha_creacion": "2024-01-02T10:00:00",
        },
        {
            "id": "order-3",
            "numero_orden": "ORD-003",
            "id_cliente": "client-456",
            "estado": "PENDING",
            "fecha_creacion": "2024-01-03T10:00:00",
        }
    ]



