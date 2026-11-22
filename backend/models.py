"""The records the backend holds and the shapes its API sends and receives."""

from datetime import date, datetime
from decimal import Decimal
from enum import StrEnum
from typing import Annotated, Literal

from pydantic import BaseModel, Field, PlainSerializer, WithJsonSchema

# Kept as Decimal in the code, but sent as a JSON number, which is what the
# dashboard and the agent read. Pydantic would otherwise send a string.
Money = Annotated[
    Decimal,
    Field(decimal_places=2),
    PlainSerializer(float, return_type=float, when_used="json"),
    WithJsonSchema({"type": "number"}),
]


class ClaimStatus(StrEnum):
    WAITING = "waiting"
    IN_PROGRESS = "in_progress"
    WAITING_FOR_SIGN_OFF = "waiting_for_sign_off"
    DECIDED = "decided"


class Item(BaseModel):
    description: str
    category: str
    amount: Money


class Document(BaseModel):
    name: str
    type: str
    content: str


class SubmittedClaim(BaseModel):
    """A claim as the customer submitted it."""

    claim_id: str
    policy_id: str
    customer_id: str
    claim_type: str
    submitted_on: date
    incident_date: date
    incident_location: str
    summary: str
    story: str
    items: list[Item]
    amount_claimed: Money
    documents: list[Document]


class DecisionType(StrEnum):
    APPROVE = "approve"
    DECLINE = "decline"
    REFER = "refer"


class StepKind(StrEnum):
    TOOL_CALL = "tool_call"
    TOOL_RESULT = "tool_result"
    REPLY = "reply"


Text = Annotated[str, Field(min_length=1)]


class Approve(BaseModel, extra="forbid"):
    decision: Literal[DecisionType.APPROVE]
    payout: Annotated[Money, Field(gt=0)]
    explanation: Text
    policy_section: Text


class Decline(BaseModel, extra="forbid"):
    decision: Literal[DecisionType.DECLINE]
    explanation: Text
    policy_section: Text


class Refer(BaseModel, extra="forbid"):
    decision: Literal[DecisionType.REFER]
    explanation: Text
    policy_section: Text


Decision = Annotated[Approve | Decline | Refer, Field(discriminator="decision")]


class ClaimSummary(BaseModel):
    claim_id: str
    claim_type: str
    summary: str
    amount_claimed: Money
    status: ClaimStatus
    decision: Decision | None


class QueuedClaim(ClaimSummary):
    """A claim as the queue lists it, for handlers.

    Only the queue names the customer. Starting, deciding and signing off a
    claim return its summary to the agent, so the name stays out of it.
    """

    customer_name: str


class NewStep(BaseModel, extra="forbid"):
    kind: StepKind
    text: Text


class Step(NewStep):
    recorded_at: datetime


class PaymentRequest(BaseModel, extra="forbid"):
    amount: Money


class Payment(PaymentRequest):
    paid_at: datetime


class SignOffRequest(BaseModel, extra="forbid"):
    handler_id: str


class SignOff(SignOffRequest):
    handler_name: str
    signed_off_at: datetime


class Claim(SubmittedClaim):
    status: ClaimStatus
    decision: Decision | None
    payment: Payment | None
    sign_off: SignOff | None
    steps: list[Step]


class Trip(BaseModel):
    destination: str
    departs_on: date
    returns_on: date
    trip_cost: Money


class Plan(BaseModel):
    plan: str
    name: str
    trip_cancellation_max: Money
    trip_delay_waiting_hours: int
    trip_delay_max: Money
    baggage_delay_waiting_hours: int
    baggage_delay_max: Money
    baggage_max: Money
    per_item_limit: Money
    passport_max: Money
    emergency_medical_max: Money
    deductible: Money


class AddOn(BaseModel):
    add_on: str
    name: str
    effect: str
    electronics_per_item_limit: Money | None = None


class Plans(BaseModel):
    """The plan catalog in `data/plans.json`."""

    plans: list[Plan]
    deductible_applies_to: list[str]
    add_ons: list[AddOn]


class PolicyRecord(BaseModel):
    """A policy as `data/policies.json` holds it, with its plan and add-ons by name."""

    policy_id: str
    customer_id: str
    plan: str
    add_ons: list[str]
    purchased_on: date
    sold_through: str
    trip: Trip
    travelers: list[str]
    status: str


class Policy(BaseModel):
    policy_id: str
    customer_id: str
    plan: Plan
    add_ons: list[AddOn]
    deductible_applies_to: list[str]
    purchased_on: date
    sold_through: str
    trip: Trip
    travelers: list[str]
    status: str


class PreviousClaim(BaseModel):
    claim_id: str
    filed_on: date
    incident_date: date
    claim_type: str
    summary: str
    outcome: str
    amount_paid: Money


class ClaimHistory(BaseModel):
    """A customer's claim history, without their contact details or date of birth."""

    customer_id: str
    name: str
    customer_since: date
    previous_claims: list[PreviousClaim]


class Handler(BaseModel):
    handler_id: str
    name: str
    role: str


class Company(BaseModel):
    payout_approval_limit: Money


class Check(StrEnum):
    OK = "ok"
    FAILED = "failed"


class Health(BaseModel):
    """Whether the backend can serve requests, and which check failed if not."""

    status: Check
    database: Check
    policy_wording: Check
    instructions: Check
