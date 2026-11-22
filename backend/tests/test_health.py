from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from backend import routes
from backend.main import app

HEALTHY = {
    "status": "ok",
    "database": "ok",
    "policy_wording": "ok",
    "instructions": "ok",
}


def test_a_healthy_backend(client: TestClient):
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == HEALTHY


def test_an_empty_database_fails_the_check(client: TestClient, database: Path):
    database.write_bytes(b"")
    response = client.get("/api/health")
    assert response.status_code == 503
    assert response.json() == HEALTHY | {"status": "failed", "database": "failed"}


def test_a_missing_database_fails_without_being_created(
    client: TestClient, database: Path
):
    database.unlink()
    response = client.get("/api/health")
    assert response.status_code == 503
    assert response.json()["database"] == "failed"
    assert not database.exists()


def test_missing_policy_wording_fails_the_check(
    client: TestClient, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
):
    monkeypatch.setattr(routes, "POLICY_WORDING", tmp_path / "missing.md")
    response = client.get("/api/health")
    assert response.status_code == 503
    assert response.json() == HEALTHY | {
        "status": "failed",
        "policy_wording": "failed",
    }


def test_missing_instructions_fail_the_check(
    client: TestClient, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
):
    monkeypatch.setattr(routes, "INSTRUCTIONS", tmp_path / "missing.md")
    response = client.get("/api/health")
    assert response.status_code == 503
    assert response.json() == HEALTHY | {"status": "failed", "instructions": "failed"}


def test_a_relative_database_path_is_checked(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("UNDERCOVER_DB", "relative.db")
    with TestClient(app) as client:
        assert client.get("/api/health").json() == HEALTHY
