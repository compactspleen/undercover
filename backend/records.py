"""Reading UnderCover's records from the database."""

import sqlite3
from decimal import Decimal

from backend.models import (
    Claim,
    ClaimHistory,
    ClaimSummary,
    Handler,
    Policy,
)

TRIP_COLUMNS = ("destination", "departs_on", "returns_on", "trip_cost")


class NotFound(Exception):
    """The request names a record that doesn't exist."""


def claim_row(connection: sqlite3.Connection, claim_id: str) -> dict[str, object]:
    """Return the claim's own row, or raise NotFound."""
    row = connection.execute(
        "SELECT * FROM claims WHERE claim_id = ?", (claim_id,)
    ).fetchone()
    if row is None:
        raise NotFound(f"There is no claim {claim_id}")
    return row


def find_summary(connection: sqlite3.Connection, claim_id: str) -> ClaimSummary:
    """Return the claim's summary, status and decision."""
    return ClaimSummary.model_validate(
        claim_row(connection, claim_id)
        | {"decision": decision_row(connection, claim_id)}
    )


def list_claims(connection: sqlite3.Connection) -> list[ClaimSummary]:
    """Return the queue in order."""
    rows = connection.execute("SELECT claim_id FROM claims ORDER BY rowid").fetchall()
    return [find_summary(connection, row["claim_id"]) for row in rows]


def find_claim(connection: sqlite3.Connection, claim_id: str) -> Claim:
    """Return the claim in full, with its decision, payment, sign-off and steps."""
    claim = claim_row(connection, claim_id)
    return Claim.model_validate(
        claim
        | {
            "items": rows(
                connection,
                "SELECT * FROM items WHERE claim_id = ? ORDER BY rowid",
                claim_id,
            ),
            "documents": rows(
                connection,
                "SELECT * FROM documents WHERE claim_id = ? ORDER BY rowid",
                claim_id,
            ),
            "decision": decision_row(connection, claim_id),
            "payment": connection.execute(
                "SELECT amount, paid_at FROM payments WHERE claim_id = ?", (claim_id,)
            ).fetchone(),
            "sign_off": connection.execute(
                "SELECT handler_id, name AS handler_name, signed_off_at "
                "FROM sign_offs JOIN handlers USING (handler_id) WHERE claim_id = ?",
                (claim_id,),
            ).fetchone(),
            "steps": rows(
                connection,
                "SELECT kind, text, recorded_at FROM steps "
                "WHERE claim_id = ? ORDER BY rowid",
                claim_id,
            ),
        }
    )


def decision_row(
    connection: sqlite3.Connection, claim_id: str
) -> dict[str, object] | None:
    """Return the claim's decision, if it has one, without an empty payout."""
    row = connection.execute(
        "SELECT decision, payout, explanation, policy_section FROM decisions "
        "WHERE claim_id = ?",
        (claim_id,),
    ).fetchone()
    if row is None:
        return None
    return {name: value for name, value in row.items() if value is not None}


def approved_payout(connection: sqlite3.Connection, claim_id: str) -> Decimal:
    """Return the payout on the claim's approval."""
    return connection.execute(
        "SELECT payout FROM decisions WHERE claim_id = ?", (claim_id,)
    ).fetchone()["payout"]


def payout_approval_limit(connection: sqlite3.Connection) -> Decimal:
    """Return the largest payout that needs no handler's sign-off."""
    return connection.execute("SELECT * FROM company").fetchone()[
        "payout_approval_limit"
    ]


def rows(
    connection: sqlite3.Connection, query: str, *parameters: object
) -> list[dict[str, object]]:
    """Return every row a query selects."""
    return connection.execute(query, parameters).fetchall()


def find_policy(connection: sqlite3.Connection, claim_id: str) -> Policy:
    """Return the claim's policy, with its plan, add-ons and travelers."""
    policy = connection.execute(
        "SELECT * FROM policies WHERE policy_id = ?",
        (claim_row(connection, claim_id)["policy_id"],),
    ).fetchone()
    return Policy.model_validate(
        policy
        | {
            "plan": connection.execute(
                "SELECT * FROM plans WHERE plan = ?", (policy["plan"],)
            ).fetchone(),
            "add_ons": connection.execute(
                "SELECT add_ons.* FROM add_ons JOIN policy_add_ons USING (add_on) "
                "WHERE policy_id = ? ORDER BY policy_add_ons.rowid",
                (policy["policy_id"],),
            ).fetchall(),
            "deductible_applies_to": column(
                connection, "SELECT claim_type FROM deductible_claim_types"
            ),
            "trip": {name: policy[name] for name in TRIP_COLUMNS},
            "travelers": column(
                connection,
                "SELECT name FROM travelers WHERE policy_id = ? ORDER BY rowid",
                policy["policy_id"],
            ),
        }
    )


def column(
    connection: sqlite3.Connection, select: str, *parameters: object
) -> list[object]:
    """Return the one column a query selects, as a list."""
    return [next(iter(row.values())) for row in rows(connection, select, *parameters)]


def find_history(connection: sqlite3.Connection, claim_id: str) -> ClaimHistory:
    """Return the claim's customer and their previous claims."""
    customer_id = claim_row(connection, claim_id)["customer_id"]
    customer = connection.execute(
        "SELECT * FROM customers WHERE customer_id = ?", (customer_id,)
    ).fetchone()
    previous_claims = connection.execute(
        "SELECT * FROM previous_claims WHERE customer_id = ? ORDER BY rowid",
        (customer_id,),
    ).fetchall()
    return ClaimHistory.model_validate(customer | {"previous_claims": previous_claims})


def find_handler(connection: sqlite3.Connection, handler_id: str) -> Handler:
    """Return the handler, or raise NotFound."""
    row = connection.execute(
        "SELECT * FROM handlers WHERE handler_id = ?", (handler_id,)
    ).fetchone()
    if row is None:
        raise NotFound(f"There is no handler {handler_id}")
    return Handler.model_validate(row)


def list_handlers(connection: sqlite3.Connection) -> list[Handler]:
    """Return the claims handlers."""
    rows = connection.execute("SELECT * FROM handlers ORDER BY rowid").fetchall()
    return [Handler.model_validate(row) for row in rows]
