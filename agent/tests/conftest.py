from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from agent import backend
from backend.main import app


@pytest.fixture(autouse=True)
def database(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    path = tmp_path / "undercover.db"
    monkeypatch.setenv("UNDERCOVER_DB", str(path))
    return path


@pytest.fixture(autouse=True)
def no_model_key(monkeypatch: pytest.MonkeyPatch) -> None:
    """Make a test that forgets its stub model fail, not call OpenRouter."""
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)


@pytest.fixture
def in_process(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    """Point the agent at the backend running in-process on the test database."""
    monkeypatch.setattr(backend, "client", lambda: TestClient(app))
    return TestClient(app)
