"""The API's operations."""

import sqlite3
from collections.abc import Iterator
from contextlib import closing
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, Request, Response
from fastapi.responses import PlainTextResponse

from backend import actions, records
from backend.database import connect
from backend.models import (
    Check,
    Claim,
    ClaimHistory,
    ClaimSummary,
    Decision,
    Handler,
    Health,
    NewStep,
    Payment,
    PaymentRequest,
    Policy,
    QueuedClaim,
    SignOffRequest,
    Step,
)

POLICY_WORDING = Path(__file__).parent.parent / "data" / "policy_wording.md"
INSTRUCTIONS = Path(__file__).parent / "instructions.md"

router = APIRouter(prefix="/api")


class MarkdownResponse(PlainTextResponse):
    media_type = "text/markdown"


def open_database(request: Request) -> Iterator[sqlite3.Connection]:
    """Open the database for one request."""
    with closing(connect(request.app.state.database_path)) as connection:
        yield connection


Database = Annotated[sqlite3.Connection, Depends(open_database)]


def check_database(path: Path) -> Check:
    """Read the claims table read-only, so the check can't create an empty file."""
    try:
        with closing(
            sqlite3.connect(f"{path.resolve().as_uri()}?mode=ro", uri=True)
        ) as connection:
            connection.execute("SELECT 1 FROM claims LIMIT 1")
    except sqlite3.Error:
        return Check.FAILED
    return Check.OK


def check_file(path: Path) -> Check:
    return Check.OK if path.is_file() else Check.FAILED


@router.get(
    "/health",
    operation_id="health",
    responses={503: {"model": Health, "description": "A check failed"}},
)
def health(request: Request, response: Response) -> Health:
    """Check that the backend can read its database and documents."""
    checks = {
        "database": check_database(request.app.state.database_path),
        "policy_wording": check_file(POLICY_WORDING),
        "instructions": check_file(INSTRUCTIONS),
    }
    is_healthy = all(check is Check.OK for check in checks.values())
    response.status_code = 200 if is_healthy else 503
    return Health(status=Check.OK if is_healthy else Check.FAILED, **checks)


@router.get("/claims", operation_id="list_claims")
def list_claims(database: Database) -> list[QueuedClaim]:
    """List the claims queue in order, with each claim's customer and status."""
    return records.list_claims(database)


@router.get("/claims/{claim_id}", operation_id="get_claim")
def get_claim(claim_id: str, database: Database) -> Claim:
    """Get a claim in full, with its decision, payment, sign-off and steps."""
    return records.find_claim(database, claim_id)


@router.get("/claims/{claim_id}/policy", operation_id="get_policy")
def get_policy(claim_id: str, database: Database) -> Policy:
    """Get the claim's policy, with its plan's limits and its add-ons."""
    return records.find_policy(database, claim_id)


@router.get("/claims/{claim_id}/history", operation_id="get_claim_history")
def get_claim_history(claim_id: str, database: Database) -> ClaimHistory:
    """Get the customer's name, customer-since date and previous claims."""
    return records.find_history(database, claim_id)


@router.get(
    "/policy-wording",
    operation_id="get_policy_wording",
    response_class=MarkdownResponse,
)
def get_policy_wording() -> str:
    """Get the policy wording as Markdown."""
    return POLICY_WORDING.read_text(encoding="utf-8")


@router.get("/handlers", operation_id="list_handlers")
def list_handlers(database: Database) -> list[Handler]:
    """List the claims handlers."""
    return records.list_handlers(database)


@router.get(
    "/instructions", operation_id="get_instructions", response_class=MarkdownResponse
)
def get_instructions() -> str:
    """Get the agent's instructions as Markdown."""
    return INSTRUCTIONS.read_text(encoding="utf-8")


@router.post("/claims/{claim_id}/start", operation_id="start_claim")
def start_claim(claim_id: str, database: Database) -> ClaimSummary:
    """Move a waiting or in-progress claim to in progress."""
    return actions.start_claim(database, claim_id)


@router.post("/claims/{claim_id}/steps", operation_id="record_step")
def record_step(claim_id: str, step: NewStep, database: Database) -> Step:
    """Add one step to the claim's activity."""
    return actions.record_step(database, claim_id, step)


@router.post("/claims/{claim_id}/decision", operation_id="record_decision")
def record_decision(
    claim_id: str, decision: Decision, database: Database
) -> ClaimSummary:
    """Record the decision on an in-progress claim and set the status."""
    return actions.record_decision(database, claim_id, decision)


@router.post("/claims/{claim_id}/payment", operation_id="pay_claim")
def pay_claim(claim_id: str, payment: PaymentRequest, database: Database) -> Payment:
    """Pay the amount on an approved claim, if the rules allow it."""
    return actions.pay_claim(database, claim_id, payment.amount)


@router.post("/claims/{claim_id}/sign-off", operation_id="sign_off")
def sign_off(
    claim_id: str, request: SignOffRequest, database: Database
) -> ClaimSummary:
    """Sign off an over-limit payout as a handler, which releases the payment."""
    return actions.sign_off(database, claim_id, request.handler_id)
