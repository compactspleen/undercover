import io
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from backend import seed
from backend.main import app

APPROVAL = {
    "decision": "approve",
    "payout": 420.0,
    "explanation": "Your flight was canceled, so we cover your costs.",
    "policy_section": "3. Trip Delay",
}


def answer(monkeypatch: pytest.MonkeyPatch, reply: str) -> None:
    monkeypatch.setattr("sys.stdin", io.StringIO(f"{reply}\n"))


def work_a_claim(client: TestClient) -> None:
    client.post("/api/claims/CLM-1001/start")
    client.post(
        "/api/claims/CLM-1001/steps", json={"kind": "reply", "text": "Approved."}
    )
    client.post("/api/claims/CLM-1001/decision", json=APPROVAL)
    client.post("/api/claims/CLM-1001/payment", json={"amount": 420.0})


def test_without_a_database_it_creates_one_without_asking(database: Path, capsys):
    assert seed.main() == 0
    assert database.exists()
    assert "every claim waiting" in capsys.readouterr().out
    with TestClient(app) as client:
        statuses = {claim["status"] for claim in client.get("/api/claims").json()}
    assert statuses == {"waiting"}


def test_rebuilding_puts_every_claim_back_in_the_queue(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
):
    work_a_claim(client)
    answer(monkeypatch, "yes")
    assert seed.main() == 0
    claims = client.get("/api/claims").json()
    assert len(claims) == 25
    assert {claim["status"] for claim in claims} == {"waiting"}
    claim = client.get("/api/claims/CLM-1001").json()
    assert claim["decision"] is None
    assert claim["payment"] is None
    assert claim["steps"] == []


def test_it_says_where_the_claims_stand_before_asking(
    client: TestClient, monkeypatch: pytest.MonkeyPatch, capsys
):
    work_a_claim(client)
    answer(monkeypatch, "yes")
    seed.main()
    output = capsys.readouterr().out
    assert "24 waiting, 0 in progress, 0 waiting for sign-off, 1 decided" in output
    assert output.index("1 decided") < output.index("Type yes")


def test_it_backs_up_the_database_it_replaces(
    client: TestClient, database: Path, monkeypatch: pytest.MonkeyPatch, capsys
):
    work_a_claim(client)
    answer(monkeypatch, "yes")
    seed.main()
    backup = database.with_name("undercover.backup.db")
    assert str(backup) in capsys.readouterr().out
    monkeypatch.setenv("UNDERCOVER_DB", str(backup))
    with TestClient(app) as backed_up:
        claim = backed_up.get("/api/claims/CLM-1001").json()
    assert claim["status"] == "decided"
    assert claim["payment"]["amount"] == 420.0


@pytest.mark.parametrize("reply", ["no", "", "y"])
def test_anything_but_yes_changes_nothing(
    client: TestClient,
    database: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys,
    reply: str,
):
    work_a_claim(client)
    before = database.read_bytes()
    answer(monkeypatch, reply)
    assert seed.main() == 1
    assert "Nothing changed" in capsys.readouterr().out
    assert database.read_bytes() == before
    assert not database.with_name("undercover.backup.db").exists()


def test_it_rebuilds_a_database_that_cant_be_read(
    client: TestClient, database: Path, monkeypatch: pytest.MonkeyPatch, capsys
):
    database.write_bytes(b"not a database")
    answer(monkeypatch, "yes")
    assert seed.main() == 0
    assert "can't be read" in capsys.readouterr().out
    assert client.get("/api/health").json()["database"] == "ok"
