from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from langchain_core.messages import AIMessage

from agent import backend, main
from agent.__main__ import run_command as command
from agent.tests.stub_model import approval, call, referral, stub
from backend import routes


def status(client: TestClient, claim_id: str) -> str:
    with client:
        return client.get(f"/api/claims/{claim_id}").json()["status"]


def queue(client: TestClient) -> list[str]:
    with client:
        return [claim["claim_id"] for claim in client.get("/api/claims").json()]


def refer_each(claim_ids: list[str]) -> list[AIMessage]:
    return [
        reply
        for claim_id in claim_ids
        for reply in (referral(claim_id), AIMessage(content="Referred."))
    ]


def use_model(monkeypatch: pytest.MonkeyPatch, *replies: AIMessage) -> None:
    model = stub(*replies)
    monkeypatch.setattr(main, "model", lambda: model)


def test_one_claim(in_process: TestClient, monkeypatch, capsys):
    use_model(
        monkeypatch,
        approval("CLM-1001", 420.0),
        call("pay_claim", claim_id="CLM-1001", amount=420.0),
        AIMessage(content="Approved and paid."),
    )
    assert command(["CLM-1001"]) == 0
    assert capsys.readouterr().out == "CLM-1001 approve $420.00\n"
    assert status(in_process, "CLM-1002") == "waiting"


def test_an_approval_waiting_for_sign_off(in_process: TestClient, monkeypatch, capsys):
    use_model(
        monkeypatch,
        approval("CLM-1003", 1250.0),
        call("pay_claim", claim_id="CLM-1003", amount=1250.0),
        AIMessage(content="Approved."),
    )
    assert command(["CLM-1003"]) == 0
    assert capsys.readouterr().out == (
        "CLM-1003 approve $1,250.00, waiting for sign-off\n"
    )


def test_every_waiting_claim_in_queue_order(
    in_process: TestClient, monkeypatch, capsys
):
    with in_process as client:
        client.post("/api/claims/CLM-1002/start")
    waiting = [claim_id for claim_id in queue(in_process) if claim_id != "CLM-1002"]
    use_model(monkeypatch, *refer_each(waiting))
    assert command([]) == 0
    output = capsys.readouterr().out
    assert output == "".join(f"{claim_id} refer\n" for claim_id in waiting)
    assert status(in_process, "CLM-1002") == "in_progress"


def test_the_queue_stops_at_the_first_failure(
    in_process: TestClient, monkeypatch, capsys
):
    use_model(
        monkeypatch,
        *refer_each(["CLM-1001"]),
        AIMessage(content="I can't decide."),
    )
    assert command([]) == 1
    output = capsys.readouterr()
    assert output.out == "CLM-1001 refer\n"
    assert output.err == "CLM-1002: the run ended without a decision\n"
    assert status(in_process, "CLM-1003") == "waiting"


def test_the_output_holds_no_claim_details(in_process: TestClient, monkeypatch, capsys):
    use_model(
        monkeypatch,
        call("get_claim", claim_id="CLM-1001"),
        call("get_claim_history", claim_id="CLM-1001"),
        referral("CLM-1001"),
        AIMessage(content="Referred."),
    )
    command(["CLM-1001"])
    output = capsys.readouterr()
    assert output.out == "CLM-1001 refer\n"
    assert output.err == ""


def test_without_the_backend(monkeypatch, capsys):
    monkeypatch.setattr(backend, "BACKEND_URL", "http://127.0.0.1:9")
    assert command(["CLM-1001"]) == 1
    assert capsys.readouterr().err == "Start the backend with npm run dev\n"


def test_a_backend_that_cant_read_its_database(
    in_process: TestClient, database: Path, capsys
):
    database.write_bytes(b"")
    assert command(["CLM-1001"]) == 1
    output = capsys.readouterr()
    assert output.out == ""
    assert output.err == "The backend is running but can't read its database\n"


def test_a_backend_missing_its_documents(
    in_process: TestClient, monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys
):
    monkeypatch.setattr(routes, "POLICY_WORDING", tmp_path / "missing.md")
    monkeypatch.setattr(routes, "INSTRUCTIONS", tmp_path / "missing.md")
    assert command([]) == 1
    assert capsys.readouterr().err == (
        "The backend is running but can't read the policy wording "
        "or the agent's instructions\n"
    )
