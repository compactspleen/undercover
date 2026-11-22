from pathlib import Path
from typing import NamedTuple

import pytest
from fastapi.testclient import TestClient

INSTRUCTIONS = Path(__file__).parent.parent / "instructions.md"
EXPLANATION = "The airline canceled your flight, so we pay your costs."


def approve(payout: float) -> dict[str, object]:
    return {
        "decision": "approve",
        "payout": payout,
        "explanation": EXPLANATION,
        "policy_section": "3. Trip Delay",
    }


def rejection(decision: str) -> dict[str, object]:
    return {
        "decision": decision,
        "explanation": "The wording doesn't cover this.",
        "policy_section": "9. General exclusions",
    }


class Answer(NamedTuple):
    status_code: int
    body: dict[str, object]


def start(client: TestClient, claim_id: str = "CLM-1001") -> Answer:
    response = client.post(f"/api/claims/{claim_id}/start")
    return Answer(response.status_code, response.json())


def decide(
    client: TestClient, decision: dict[str, object], claim_id: str = "CLM-1001"
) -> Answer:
    response = client.post(f"/api/claims/{claim_id}/decision", json=decision)
    return Answer(response.status_code, response.json())


def pay(client: TestClient, amount: float, claim_id: str = "CLM-1001") -> Answer:
    response = client.post(f"/api/claims/{claim_id}/payment", json={"amount": amount})
    return Answer(response.status_code, response.json())


def sign_off(client: TestClient, handler_id: str = "HND-01") -> Answer:
    response = client.post(
        "/api/claims/CLM-1001/sign-off", json={"handler_id": handler_id}
    )
    return Answer(response.status_code, response.json())


def status(client: TestClient, claim_id: str = "CLM-1001") -> str:
    return client.get(f"/api/claims/{claim_id}").json()["status"]


def approve_over_the_limit(client: TestClient) -> None:
    start(client)
    decide(client, approve(1250.0))


def test_the_instructions_are_the_backends_file(client: TestClient):
    response = client.get("/api/instructions")
    assert response.text == INSTRUCTIONS.read_text(encoding="utf-8")


def test_starting_a_claim_puts_it_in_progress(client: TestClient):
    assert start(client).body["status"] == "in_progress"
    assert status(client) == "in_progress"


def test_a_decided_claim_cant_be_started(client: TestClient):
    start(client)
    decide(client, rejection("refer"))
    response = start(client)
    assert response.status_code == 409
    assert response.body == {"detail": "This claim already has a decision"}


def test_steps_come_back_in_order(client: TestClient):
    start(client)
    client.post(
        "/api/claims/CLM-1001/steps", json={"kind": "tool_call", "text": "get_claim"}
    )
    client.post(
        "/api/claims/CLM-1001/steps", json={"kind": "reply", "text": "Approved."}
    )
    steps = client.get("/api/claims/CLM-1001").json()["steps"]
    assert [(step["kind"], step["text"]) for step in steps] == [
        ("tool_call", "get_claim"),
        ("reply", "Approved."),
    ]
    assert all(step["recorded_at"] for step in steps)


def test_a_claim_that_hasnt_started_takes_no_steps(client: TestClient):
    response = client.post(
        "/api/claims/CLM-1001/steps", json={"kind": "reply", "text": "Hello"}
    )
    assert response.status_code == 409
    assert response.json() == {"detail": "This claim hasn't been started"}


def test_a_decided_claim_still_takes_steps(client: TestClient):
    start(client)
    decide(client, approve(420.0))
    response = client.post(
        "/api/claims/CLM-1001/steps", json={"kind": "reply", "text": "Paid."}
    )
    assert response.status_code == 200


@pytest.mark.parametrize(
    ("setup", "reason"),
    [
        (lambda client: None, "This claim hasn't been started"),
        (approve_over_the_limit, "This claim already has a decision"),
        (
            lambda client: (start(client), decide(client, approve(420.0))),
            "This claim already has a decision",
        ),
    ],
    ids=["waiting", "waiting for sign-off", "decided"],
)
def test_a_decision_needs_a_claim_in_progress(client: TestClient, setup, reason):
    setup(client)
    response = decide(client, rejection("decline"))
    assert response.status_code == 409
    assert response.body == {"detail": reason}


def test_an_approval_within_the_limit_decides_the_claim(client: TestClient):
    start(client)
    assert decide(client, approve(420.0)).body["status"] == "decided"
    claim = client.get("/api/claims/CLM-1001").json()
    assert claim["decision"] == approve(420.0)


def test_an_approval_over_the_limit_waits_for_sign_off(client: TestClient):
    start(client)
    assert decide(client, approve(1250.0)).body["status"] == "waiting_for_sign_off"


def test_an_approval_of_exactly_the_limit_is_within_it(client: TestClient):
    start(client)
    assert decide(client, approve(1000.0)).body["status"] == "decided"


@pytest.mark.parametrize("decision", ["decline", "refer"])
def test_a_decline_or_referral_decides_the_claim(client: TestClient, decision: str):
    start(client)
    assert decide(client, rejection(decision)).body["status"] == "decided"
    assert client.get("/api/claims/CLM-1001").json()["decision"] == rejection(decision)


def test_the_queue_shows_each_claims_decision_and_payout(client: TestClient):
    start(client)
    assert decide(client, approve(420.0)).body["decision"] == approve(420.0)
    start(client, "CLM-1002")
    decide(client, rejection("decline"), "CLM-1002")
    queue = client.get("/api/claims").json()
    decisions = {claim["claim_id"]: claim["decision"] for claim in queue}
    assert decisions["CLM-1001"] == approve(420.0)
    assert decisions["CLM-1002"] == rejection("decline")
    assert decisions["CLM-1003"] is None


def test_a_decline_with_a_payout_is_rejected(client: TestClient):
    start(client)
    response = decide(client, rejection("decline") | {"payout": 100.0})
    assert response.status_code == 422
    assert status(client) == "in_progress"


def test_an_approval_needs_a_payout_in_cents(client: TestClient):
    start(client)
    assert decide(client, approve(420.001)).status_code == 422


def test_a_second_decision_is_refused(client: TestClient):
    start(client)
    decide(client, rejection("refer"))
    assert decide(client, approve(420.0)).status_code == 409
    assert client.get("/api/claims/CLM-1001").json()["decision"]["decision"] == "refer"


def test_paying_an_approval_within_the_limit(client: TestClient):
    start(client)
    decide(client, approve(420.0))
    assert pay(client, 420.0).body["amount"] == 420.0
    payment = client.get("/api/claims/CLM-1001").json()["payment"]
    assert payment["amount"] == 420.0
    assert payment["paid_at"]


def approve_and_pay(client: TestClient) -> None:
    start(client)
    decide(client, approve(420.0))
    pay(client, 420.0)


@pytest.mark.parametrize(
    ("setup", "amount", "reason"),
    [
        (
            approve_over_the_limit,
            1250.0,
            "A payout over $1,000.00 waits for a handler's sign-off",
        ),
        (
            lambda client: (start(client), decide(client, approve(420.0))),
            400.0,
            "The amount doesn't match the approved payout of $420.00",
        ),
        (approve_and_pay, 420.0, "This claim has already been paid"),
        (
            lambda client: (start(client), decide(client, rejection("decline"))),
            420.0,
            "This claim has no approval to pay",
        ),
        (
            lambda client: (start(client), decide(client, rejection("refer"))),
            420.0,
            "This claim has no approval to pay",
        ),
    ],
    ids=["over the limit", "wrong amount", "already paid", "declined", "referred"],
)
def test_payments_the_rules_refuse(client: TestClient, setup, amount, reason):
    setup(client)
    response = pay(client, amount)
    assert response.status_code == 409
    assert response.body == {"detail": reason}


def test_an_over_limit_claim_stays_unpaid_until_sign_off(client: TestClient):
    approve_over_the_limit(client)
    pay(client, 1250.0)
    assert client.get("/api/claims/CLM-1001").json()["payment"] is None


def test_sign_off_decides_the_claim_and_releases_the_payment(client: TestClient):
    approve_over_the_limit(client)
    assert sign_off(client).body["status"] == "decided"
    claim = client.get("/api/claims/CLM-1001").json()
    assert claim["status"] == "decided"
    assert claim["sign_off"]["handler_id"] == "HND-01"
    assert claim["sign_off"]["handler_name"] == "Dana Whitfield"
    assert claim["sign_off"]["signed_off_at"]
    assert claim["payment"]["amount"] == 1250.0


def test_a_signed_off_claim_cant_be_paid_again(client: TestClient):
    approve_over_the_limit(client)
    sign_off(client)
    response = pay(client, 1250.0)
    assert response.status_code == 409
    assert response.body == {"detail": "This claim has already been paid"}


def test_sign_off_needs_a_claim_waiting_for_it(client: TestClient):
    start(client)
    decide(client, approve(420.0))
    response = sign_off(client)
    assert response.status_code == 409
    assert response.body == {"detail": "This claim isn't waiting for sign-off"}


def test_sign_off_by_an_unknown_handler(client: TestClient):
    approve_over_the_limit(client)
    response = sign_off(client, "HND-99")
    assert response.status_code == 404
    assert response.body == {"detail": "There is no handler HND-99"}
    assert status(client) == "waiting_for_sign_off"


def test_writes_to_an_unknown_claim_are_not_found(client: TestClient):
    assert start(client, "CLM-9999").status_code == 404
    assert decide(client, approve(420.0), "CLM-9999").status_code == 404
    assert pay(client, 420.0, "CLM-9999").status_code == 404


def test_decisions_survive_a_restart(client: TestClient):
    start(client)
    decide(client, rejection("refer"))
    with TestClient(client.app) as restarted:
        assert status(restarted) == "decided"
