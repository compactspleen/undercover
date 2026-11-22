from pathlib import Path

from fastapi.testclient import TestClient

from backend.main import app


def test_starting_creates_the_database_with_every_claim_waiting(
    database: Path, client: TestClient
):
    claims = client.get("/api/claims").json()
    assert database.exists()
    assert len(claims) == 25
    assert {claim["status"] for claim in claims} == {"waiting"}


def test_starting_again_keeps_the_existing_database(database: Path):
    with TestClient(app):
        pass
    before = database.read_bytes()
    with TestClient(app) as client:
        assert len(client.get("/api/claims").json()) == 25
    assert database.read_bytes() == before


def test_the_database_file_comes_from_the_environment(tmp_path: Path, monkeypatch):
    path = tmp_path / "elsewhere" / "claims.db"
    monkeypatch.setenv("UNDERCOVER_DB", str(path))
    with TestClient(app) as client:
        assert client.get("/api/claims").status_code == 200
    assert path.exists()


def test_the_queue_is_in_order_with_each_claims_summary(client: TestClient):
    claims = client.get("/api/claims").json()
    assert claims[0] == {
        "claim_id": "CLM-1001",
        "claim_type": "trip_delay",
        "summary": "Flight home canceled by the airline, rebooked the next morning",
        "amount_claimed": 420.0,
        "status": "waiting",
        "decision": None,
    }
    assert [claim["claim_id"] for claim in claims][:3] == [
        "CLM-1001",
        "CLM-1002",
        "CLM-1003",
    ]


def test_amounts_are_json_numbers(client: TestClient):
    response = client.get("/api/claims")
    assert '"amount_claimed":420.0' in response.text


def test_a_claim_has_its_story_items_and_documents(client: TestClient):
    claim = client.get("/api/claims/CLM-1001").json()
    assert claim["story"].startswith("My flight home from Rome")
    assert claim["items"][0] == {
        "description": "Airport hotel, one night",
        "category": "accommodation",
        "amount": 245.0,
    }
    assert [document["name"] for document in claim["documents"]][0] == (
        "Meridian Air cancellation notice"
    )
    assert claim["decision"] is None
    assert claim["payment"] is None
    assert claim["sign_off"] is None
    assert claim["steps"] == []


def test_a_claims_policy_has_its_plan_and_add_ons(client: TestClient):
    policy = client.get("/api/claims/CLM-1001/policy").json()
    assert policy["policy_id"] == "POL-2001"
    assert policy["plan"]["name"] == "UnderCover Premium"
    assert policy["plan"]["baggage_max"] == 1500.0
    assert policy["add_ons"] == []
    assert policy["deductible_applies_to"] == ["baggage", "emergency_medical"]
    assert policy["trip"]["destination"] == "Rome, Italy"
    assert policy["travelers"] == ["Maya Patel"]


def test_a_policy_with_add_ons_lists_them(client: TestClient):
    policies = [
        client.get(f"/api/claims/{claim['claim_id']}/policy").json()
        for claim in client.get("/api/claims").json()
    ]
    add_ons = {add_on["add_on"] for policy in policies for add_on in policy["add_ons"]}
    assert add_ons
    assert all(add_on["effect"] for policy in policies for add_on in policy["add_ons"])


def test_the_claim_history_leaves_out_personal_details(client: TestClient):
    response = client.get("/api/claims/CLM-1001/history")
    history = response.json()
    assert history["customer_id"] == "CUS-3001"
    assert history["name"] == "Maya Patel"
    assert history["previous_claims"][0]["claim_id"] == "CLM-0412"
    assert history["previous_claims"][0]["amount_paid"] == 140.0
    for detail in ("email", "phone", "address", "date_of_birth", "maya.patel@"):
        assert detail not in response.text


def test_the_policy_wording(client: TestClient):
    response = client.get("/api/policy-wording")
    assert response.text.startswith("# UnderCover Travel Insurance: Policy Wording")


def test_the_handlers(client: TestClient):
    handlers = client.get("/api/handlers").json()
    assert [handler["name"] for handler in handlers] == [
        "Dana Whitfield",
        "Marcus Oyelaran",
        "Priya Raman",
    ]


def test_an_unknown_claim_is_not_found(client: TestClient):
    for path in ("", "/policy", "/history"):
        response = client.get(f"/api/claims/CLM-9999{path}")
        assert response.status_code == 404
        assert response.json() == {"detail": "There is no claim CLM-9999"}
