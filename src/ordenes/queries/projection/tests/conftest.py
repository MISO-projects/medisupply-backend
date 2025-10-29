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


@pytest.fixture
def healthy_deps():
    return {
        "db": FakeDB(should_fail=False),
    }


@pytest.fixture
def failing_db_deps():
    return {
        "db": FakeDB(should_fail=True),
    }



