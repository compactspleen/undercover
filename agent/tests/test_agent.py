import json

import httpx
import pytest
from fastapi.testclient import TestClient
from langchain_core.messages import AIMessage
from langchain_core.rate_limiters import BaseRateLimiter, InMemoryRateLimiter

from agent import backend, main, tools
from agent.main import InvalidSetting, RunFailed
from agent.tests.stub_model import StubModel, approval, call, referral, stub

INSTRUCTIONS = "backend/instructions.md"


def status(client: TestClient, claim_id: str) -> str:
    with client:
        return client.get(f"/api/claims/{claim_id}").json()["status"]


def reading(claim_id: str) -> list[AIMessage]:
    return [
        call("get_claim", claim_id=claim_id),
        call("get_policy", claim_id=claim_id),
        call("get_claim_history", claim_id=claim_id),
        call("get_policy_wording"),
    ]


def test_the_model_gets_the_backends_instructions(in_process: TestClient):
    model = stub(referral("CLM-1001"), AIMessage(content="Referred."))
    main.run("CLM-1001", "thread-1", model)
    with open(INSTRUCTIONS, encoding="utf-8") as file:
        assert model.prompts[0][0].content == file.read()


def test_working_a_claim_to_an_approval_and_payment(in_process: TestClient):
    model = stub(
        *reading("CLM-1001"),
        approval("CLM-1001", 420.0),
        call("pay_claim", claim_id="CLM-1001", amount=420.0),
        AIMessage(content="Approved and paid $420.00."),
    )
    outcome = main.run("CLM-1001", "thread-1", model)
    with in_process as client:
        worked = client.get("/api/claims/CLM-1001").json()
    assert outcome.status == "decided"
    assert worked["status"] == "decided"
    assert worked["payment"]["amount"] == 420.0
    steps = worked["steps"]
    assert [step["kind"] for step in steps] == [
        *["tool_call", "tool_result"] * 6,
        "reply",
    ]
    assert steps[0]["text"] == 'get_claim {"claim_id": "CLM-1001"}'
    assert steps[1]["text"].startswith('get_claim: {"claim_id": "CLM-1001"')
    assert steps[-1]["text"] == "Approved and paid $420.00."


def test_an_over_limit_payment_waits_for_sign_off(in_process: TestClient):
    model = stub(
        approval("CLM-1003", 1250.0),
        call("pay_claim", claim_id="CLM-1003", amount=1250.0),
        AIMessage(content="Approved; the payment waits for sign-off."),
    )
    outcome = main.run("CLM-1003", "thread-1", model)
    with in_process as client:
        worked = client.get("/api/claims/CLM-1003").json()
    assert outcome.status == "waiting_for_sign_off"
    assert worked["payment"] is None
    assert any(
        step["kind"] == "tool_result"
        and "A payout over $1,000.00 waits for a handler's sign-off" in step["text"]
        for step in worked["steps"]
    )


def test_the_claim_tool_leaves_out_the_work_on_it(in_process: TestClient):
    fields = json.loads(tools.get_claim.invoke({"claim_id": "CLM-1001"}))
    assert fields["claim_id"] == "CLM-1001"
    assert fields["story"]
    for name in ("decision", "payment", "sign_off", "steps"):
        assert name not in fields


def test_a_refused_decision_goes_back_to_the_model(in_process: TestClient):
    result = tools.record_decision.invoke(
        {
            "claim_id": "CLM-1001",
            "decision": {
                "decision": "decline",
                "explanation": "Not covered.",
                "policy_section": "9. General exclusions",
            },
        }
    )
    assert result == "Refused (409): This claim hasn't been started"


def test_a_payment_the_backend_cant_read_goes_back_to_the_model(
    in_process: TestClient,
):
    result = tools.pay_claim.invoke({"claim_id": "CLM-1001", "amount": 420.001})
    assert result.startswith("Refused (422): ")


def failing_backend(request: httpx.Request) -> httpx.Response:
    if request.url.path == "/api/claims/CLM-1001":
        return httpx.Response(500, text="Internal Server Error")
    return httpx.Response(200, text="Work one claim.")


def test_a_server_error_stops_the_run(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(
        backend,
        "client",
        lambda: httpx.Client(
            base_url="http://backend", transport=httpx.MockTransport(failing_backend)
        ),
    )
    model = stub(call("get_claim", claim_id="CLM-1001"), AIMessage(content="Done."))
    with pytest.raises(httpx.HTTPStatusError):
        main.run("CLM-1001", "thread-1", model)


def test_a_run_without_a_decision_fails(in_process: TestClient):
    model = stub(AIMessage(content="I can't decide this one."))
    with pytest.raises(RunFailed, match="CLM-1001: the run ended without a decision"):
        main.run("CLM-1001", "thread-1", model)
    assert status(in_process, "CLM-1001") == "in_progress"


def test_an_approval_that_isnt_paid_fails(in_process: TestClient):
    model = stub(approval("CLM-1001", 420.0), AIMessage(content="Approved."))
    with pytest.raises(RunFailed, match="CLM-1001: approved but not paid"):
        main.run("CLM-1001", "thread-1", model)


def test_model_name(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")
    monkeypatch.delenv("MODEL_NAME", raising=False)
    assert main.model().model_name == "openai/gpt-6-luna"
    assert main.model().reasoning_effort == "low"
    monkeypatch.setenv("MODEL_NAME", "openrouter/free")
    assert main.model().model_name == "openrouter/free"
    assert main.model().reasoning_effort is None


def throttle_of(model: main.ChatOpenAI) -> InMemoryRateLimiter:
    throttle = model.rate_limiter
    assert isinstance(throttle, InMemoryRateLimiter)
    return throttle


def test_the_model_makes_at_most_20_calls_a_minute_by_default(
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")
    monkeypatch.delenv("MODEL_REQUESTS_PER_MINUTE", raising=False)
    throttle = throttle_of(main.model())
    assert throttle.requests_per_second == 20 / 60
    assert throttle.max_bucket_size == 1


@pytest.mark.parametrize(("setting", "per_minute"), [("30", 30), (" 1 ", 1), ("", 20)])
def test_model_requests_per_minute_sets_the_rate(
    monkeypatch: pytest.MonkeyPatch, setting: str, per_minute: int
):
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")
    monkeypatch.setenv("MODEL_REQUESTS_PER_MINUTE", setting)
    throttle = throttle_of(main.model())
    assert throttle.requests_per_second == per_minute / 60
    assert throttle.max_bucket_size == 1


@pytest.mark.parametrize("setting", ["fast", "0", "-5", "1.5"])
def test_a_rate_that_isnt_a_whole_number_above_zero_is_refused(
    monkeypatch: pytest.MonkeyPatch, setting: str
):
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")
    monkeypatch.setenv("MODEL_REQUESTS_PER_MINUTE", setting)
    with pytest.raises(InvalidSetting) as refusal:
        main.model()
    assert str(refusal.value) == (
        f"MODEL_REQUESTS_PER_MINUTE must be a whole number above 0, such as 20, "
        f"not {setting!r}"
    )


class CountingThrottle(BaseRateLimiter):
    """A throttle that counts how often the model waits for it, without waiting."""

    def __init__(self) -> None:
        self.waits = 0

    def acquire(self, *, blocking: bool = True) -> bool:
        self.waits += 1
        return True

    async def aacquire(self, *, blocking: bool = True) -> bool:
        return self.acquire(blocking=blocking)


def test_the_agent_waits_for_the_throttle_before_each_model_call(
    in_process: TestClient,
):
    throttle = CountingThrottle()
    model = StubModel(
        messages=iter([referral("CLM-1001"), AIMessage(content="Referred.")]),
        rate_limiter=throttle,
    )
    main.run("CLM-1001", "thread-1", model)
    assert len(model.prompts) == 2
    assert throttle.waits == 2


def test_a_model_that_cant_be_built_leaves_the_claim_waiting(
    in_process: TestClient, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.setenv("MODEL_REQUESTS_PER_MINUTE", "fast")
    with pytest.raises(InvalidSetting):
        main.run("CLM-1001", "thread-1")
    assert status(in_process, "CLM-1001") == "waiting"
