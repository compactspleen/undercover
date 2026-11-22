"""The operations that change a claim, and the rules they enforce."""

import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime
from decimal import Decimal

from backend import records
from backend.models import (
    Approve,
    Claim,
    ClaimStatus,
    ClaimSummary,
    Decision,
    NewStep,
    Payment,
    Step,
)

NOT_STARTED = "This claim hasn't been started"
ALREADY_DECIDED = "This claim already has a decision"
WHY_NOT_IN_PROGRESS = {
    ClaimStatus.WAITING: NOT_STARTED,
    ClaimStatus.WAITING_FOR_SIGN_OFF: ALREADY_DECIDED,
    ClaimStatus.DECIDED: ALREADY_DECIDED,
}


class Conflict(Exception):
    """The request isn't allowed in the claim's current state."""


@contextmanager
def transaction(connection: sqlite3.Connection) -> Iterator[None]:
    """Run a check and the write that follows it with no other write between."""
    with connection:
        connection.execute("BEGIN IMMEDIATE")
        yield


def set_status(
    connection: sqlite3.Connection, claim_id: str, status: ClaimStatus
) -> None:
    connection.execute(
        "UPDATE claims SET status = ? WHERE claim_id = ?", (status, claim_id)
    )


def start_claim(connection: sqlite3.Connection, claim_id: str) -> ClaimSummary:
    """Move a waiting or in-progress claim to in progress."""
    with transaction(connection):
        if records.find_summary(connection, claim_id).status in (
            ClaimStatus.WAITING_FOR_SIGN_OFF,
            ClaimStatus.DECIDED,
        ):
            raise Conflict(ALREADY_DECIDED)
        set_status(connection, claim_id, ClaimStatus.IN_PROGRESS)
    return records.find_summary(connection, claim_id)


def record_step(connection: sqlite3.Connection, claim_id: str, step: NewStep) -> Step:
    """Add a step to a started claim's activity."""
    recorded = Step(kind=step.kind, text=step.text, recorded_at=datetime.now(UTC))
    with transaction(connection):
        if records.find_summary(connection, claim_id).status is ClaimStatus.WAITING:
            raise Conflict(NOT_STARTED)
        connection.execute(
            "INSERT INTO steps VALUES (:claim_id, :kind, :text, :recorded_at)",
            recorded.model_dump() | {"claim_id": claim_id},
        )
    return recorded


def status_after(decision: Decision, limit: Decimal) -> ClaimStatus:
    """Return where a claim stands once this decision is recorded."""
    if isinstance(decision, Approve) and decision.payout > limit:
        return ClaimStatus.WAITING_FOR_SIGN_OFF
    return ClaimStatus.DECIDED


def record_decision(
    connection: sqlite3.Connection, claim_id: str, decision: Decision
) -> ClaimSummary:
    """Record the decision on an in-progress claim and set its status."""
    with transaction(connection):
        status = records.find_summary(connection, claim_id).status
        if status is not ClaimStatus.IN_PROGRESS:
            raise Conflict(WHY_NOT_IN_PROGRESS[status])
        connection.execute(
            "INSERT INTO decisions VALUES "
            "(:claim_id, :decision, :payout, :explanation, :policy_section)",
            {"claim_id": claim_id, "payout": None} | decision.model_dump(),
        )
        limit = records.payout_approval_limit(connection)
        set_status(connection, claim_id, status_after(decision, limit))
    return records.find_summary(connection, claim_id)


def check_payment(claim: Claim, amount: Decimal, limit: Decimal) -> None:
    """Raise Conflict unless the rules allow paying this amount on the claim."""
    decision = claim.decision
    if not isinstance(decision, Approve):
        raise Conflict("This claim has no approval to pay")
    if claim.payment is not None:
        raise Conflict("This claim has already been paid")
    if amount != decision.payout:
        raise Conflict(
            f"The amount doesn't match the approved payout of ${decision.payout:,.2f}"
        )
    if decision.payout > limit and claim.sign_off is None:
        raise Conflict(f"A payout over ${limit:,.2f} waits for a handler's sign-off")


def insert_payment(
    connection: sqlite3.Connection, claim_id: str, amount: Decimal
) -> Payment:
    payment = Payment(amount=amount, paid_at=datetime.now(UTC))
    connection.execute(
        "INSERT INTO payments VALUES (:claim_id, :amount, :paid_at)",
        payment.model_dump() | {"claim_id": claim_id},
    )
    return payment


def pay_claim(
    connection: sqlite3.Connection, claim_id: str, amount: Decimal
) -> Payment:
    """Pay the amount on an approved claim, if the rules allow it."""
    with transaction(connection):
        claim = records.find_claim(connection, claim_id)
        check_payment(claim, amount, records.payout_approval_limit(connection))
        return insert_payment(connection, claim_id, amount)


def sign_off(
    connection: sqlite3.Connection, claim_id: str, handler_id: str
) -> ClaimSummary:
    """Sign off an over-limit payout, which decides the claim and pays it."""
    with transaction(connection):
        records.find_handler(connection, handler_id)
        claim = records.find_claim(connection, claim_id)
        if claim.status is not ClaimStatus.WAITING_FOR_SIGN_OFF:
            raise Conflict("This claim isn't waiting for sign-off")
        connection.execute(
            "INSERT INTO sign_offs VALUES (?, ?, ?)",
            (claim_id, handler_id, datetime.now(UTC)),
        )
        payout = records.approved_payout(connection, claim_id)
        insert_payment(connection, claim_id, payout)
        set_status(connection, claim_id, ClaimStatus.DECIDED)
    return records.find_summary(connection, claim_id)
