"""The UnderCover Agent's tools, each a call to the backend's API."""

import json
from decimal import Decimal
from typing import Annotated, Literal

from langchain_core.tools import tool
from pydantic import BaseModel, Field, PlainSerializer, WithJsonSchema

from agent import backend

# The claim's own work, which the model doesn't need to decide it.
WORK_FIELDS = ("decision", "payment", "sign_off", "steps")

Money = Annotated[
    Decimal,
    PlainSerializer(float, return_type=float, when_used="json"),
    WithJsonSchema({"type": "number"}),
]
Explanation = Annotated[
    str,
    Field(
        description="Two or three polite, professional sentences to the customer "
        "saying what you decided and why"
    ),
]
PolicySection = Annotated[
    str,
    Field(description='The section of the policy wording, such as "3. Trip Delay"'),
]


class Approve(BaseModel):
    """Approve the claim with a payout."""

    decision: Literal["approve"]
    payout: Annotated[Money, Field(description="The payout in US dollars")]
    explanation: Explanation
    policy_section: PolicySection


class Decline(BaseModel):
    """Decline the claim."""

    decision: Literal["decline"]
    explanation: Explanation
    policy_section: PolicySection


class Refer(BaseModel):
    """Refer the claim to a handler."""

    decision: Literal["refer"]
    explanation: Explanation
    policy_section: PolicySection


@tool
def get_claim(claim_id: str) -> str:
    """Get the claim: the customer's story, the items claimed and the documents."""
    claim: dict[str, object] = json.loads(backend.get(f"/api/claims/{claim_id}"))
    return json.dumps(
        {name: value for name, value in claim.items() if name not in WORK_FIELDS}
    )


@tool
def get_policy(claim_id: str) -> str:
    """Get the claim's policy, with its plan's limits, deductible and add-ons."""
    return backend.get(f"/api/claims/{claim_id}/policy")


@tool
def get_claim_history(claim_id: str) -> str:
    """Get the customer's previous claims with UnderCover."""
    return backend.get(f"/api/claims/{claim_id}/history")


@tool
def get_policy_wording() -> str:
    """Get the policy wording, the contract that decides every claim."""
    return backend.get("/api/policy-wording")


@tool
def record_decision(
    claim_id: str,
    decision: Annotated[Approve | Decline | Refer, Field(discriminator="decision")],
) -> str:
    """Record your decision on the claim: approve, decline or refer."""
    return backend.attempt(
        f"/api/claims/{claim_id}/decision", decision.model_dump(mode="json")
    )


@tool
def pay_claim(
    claim_id: str,
    amount: Annotated[Money, Field(description="The approved payout in US dollars")],
) -> str:
    """Pay an approved claim its payout."""
    return backend.attempt(f"/api/claims/{claim_id}/payment", {"amount": float(amount)})


TOOLS = [
    get_claim,
    get_policy,
    get_claim_history,
    get_policy_wording,
    record_decision,
    pay_claim,
]
