from pathlib import Path

import pytest


@pytest.fixture(autouse=True)
def database(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    path = tmp_path / "undercover.db"
    monkeypatch.setenv("UNDERCOVER_DB", str(path))
    return path


@pytest.fixture(autouse=True)
def no_model_key(monkeypatch: pytest.MonkeyPatch) -> None:
    """Make a test that forgets its stub model fail, not call OpenRouter."""
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
