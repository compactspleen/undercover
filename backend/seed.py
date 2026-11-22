"""Building the database from UnderCover's records in `data/`.

Only the files named below are read. Nothing else in `data/` may reach the
database, because the agent must never see the handlers' own decisions.

`uv run -m backend.seed` rebuilds the database, putting every claim back in
the queue. It shows where the claims stand and asks before it replaces
anything, and keeps a backup of the database it replaces.
"""

import shutil
import sqlite3
import sys
from contextlib import closing
from pathlib import Path

from pydantic import TypeAdapter

from backend import database
from backend.models import (
    ClaimHistory,
    ClaimStatus,
    Company,
    Handler,
    Plans,
    PolicyRecord,
    SubmittedClaim,
)

DATA = Path(__file__).parent.parent / "data"
CONFIRMATION = "yes"
STATUS_WORDS = {
    ClaimStatus.WAITING: "waiting",
    ClaimStatus.IN_PROGRESS: "in progress",
    ClaimStatus.WAITING_FOR_SIGN_OFF: "waiting for sign-off",
    ClaimStatus.DECIDED: "decided",
}


def read(name: str) -> str:
    """Read one of the seed data files."""
    return (DATA / name).read_text(encoding="utf-8")


def load(connection: sqlite3.Connection) -> None:
    """Load every seed record into the database."""
    load_company(connection, Company.model_validate_json(read("company.json")))
    load_handlers(
        connection, TypeAdapter(list[Handler]).validate_json(read("handlers.json"))
    )
    load_plans(connection, Plans.model_validate_json(read("plans.json")))
    load_customers(
        connection,
        TypeAdapter(list[ClaimHistory]).validate_json(read("customers.json")),
    )
    load_policies(
        connection,
        TypeAdapter(list[PolicyRecord]).validate_json(read("policies.json")),
    )
    load_claims(
        connection, TypeAdapter(list[SubmittedClaim]).validate_json(read("claims.json"))
    )


def load_company(connection: sqlite3.Connection, company: Company) -> None:
    connection.execute(
        "INSERT INTO company VALUES (:payout_approval_limit)", company.model_dump()
    )


def load_handlers(connection: sqlite3.Connection, handlers: list[Handler]) -> None:
    connection.executemany(
        "INSERT INTO handlers VALUES (:handler_id, :name, :role)",
        [handler.model_dump() for handler in handlers],
    )


def load_plans(connection: sqlite3.Connection, plans: Plans) -> None:
    connection.executemany(
        """INSERT INTO plans VALUES (
            :plan, :name, :trip_cancellation_max, :trip_delay_waiting_hours,
            :trip_delay_max, :baggage_delay_waiting_hours, :baggage_delay_max,
            :baggage_max, :per_item_limit, :passport_max, :emergency_medical_max,
            :deductible
        )""",
        [plan.model_dump() for plan in plans.plans],
    )
    connection.executemany(
        "INSERT INTO add_ons VALUES (:add_on, :name, :effect, "
        ":electronics_per_item_limit)",
        [add_on.model_dump() for add_on in plans.add_ons],
    )
    connection.executemany(
        "INSERT INTO deductible_claim_types VALUES (?)",
        [(claim_type,) for claim_type in plans.deductible_applies_to],
    )


def load_customers(
    connection: sqlite3.Connection, customers: list[ClaimHistory]
) -> None:
    connection.executemany(
        "INSERT INTO customers VALUES (:customer_id, :name, :customer_since)",
        [customer.model_dump() for customer in customers],
    )
    connection.executemany(
        """INSERT INTO previous_claims VALUES (
            :customer_id, :claim_id, :filed_on, :incident_date, :claim_type,
            :summary, :outcome, :amount_paid
        )""",
        [
            previous.model_dump() | {"customer_id": customer.customer_id}
            for customer in customers
            for previous in customer.previous_claims
        ],
    )


def load_policies(connection: sqlite3.Connection, policies: list[PolicyRecord]) -> None:
    connection.executemany(
        """INSERT INTO policies VALUES (
            :policy_id, :customer_id, :plan, :purchased_on, :sold_through,
            :destination, :departs_on, :returns_on, :trip_cost, :status
        )""",
        [policy.model_dump() | policy.trip.model_dump() for policy in policies],
    )
    connection.executemany(
        "INSERT INTO policy_add_ons VALUES (?, ?)",
        [
            (policy.policy_id, add_on)
            for policy in policies
            for add_on in policy.add_ons
        ],
    )
    connection.executemany(
        "INSERT INTO travelers VALUES (?, ?)",
        [(policy.policy_id, name) for policy in policies for name in policy.travelers],
    )


def load_claims(connection: sqlite3.Connection, claims: list[SubmittedClaim]) -> None:
    connection.executemany(
        """INSERT INTO claims VALUES (
            :claim_id, :policy_id, :customer_id, :claim_type, :submitted_on,
            :incident_date, :incident_location, :summary, :story, :amount_claimed,
            :status
        )""",
        [claim.model_dump() | {"status": ClaimStatus.WAITING} for claim in claims],
    )
    connection.executemany(
        "INSERT INTO items VALUES (:claim_id, :description, :category, :amount)",
        [
            item.model_dump() | {"claim_id": claim.claim_id}
            for claim in claims
            for item in claim.items
        ],
    )
    connection.executemany(
        "INSERT INTO documents VALUES (:claim_id, :name, :type, :content)",
        [
            document.model_dump() | {"claim_id": claim.claim_id}
            for claim in claims
            for document in claim.documents
        ],
    )


def build(path: Path) -> None:
    """Write a new database from the seed data, then swap it in at the path."""
    path.parent.mkdir(parents=True, exist_ok=True)
    draft = path.with_name(f"{path.name}.draft")
    draft.unlink(missing_ok=True)
    with closing(database.connect(draft)) as connection:
        connection.executescript(database.SCHEMA)
        with connection:
            connection.execute("BEGIN")
            load(connection)
    draft.replace(path)


def prepare(path: Path) -> None:
    """Create the database from the seed data, unless it exists already."""
    if not path.exists():
        build(path)


def backup_path(path: Path) -> Path:
    """Name the backup so it ends like the database, which git ignores."""
    return path.with_name(f"{path.stem}.backup{path.suffix}")


def describe(path: Path) -> str:
    """Say where the claims in an existing database stand."""
    try:
        with closing(database.connect(path)) as connection:
            rows = connection.execute(
                "SELECT status, count(*) AS claims FROM claims GROUP BY status"
            ).fetchall()
    except sqlite3.Error:
        return f"{path} can't be read."
    counts = {row["status"]: row["claims"] for row in rows}
    return f"{path} has " + ", ".join(
        f"{counts.get(status, 0)} {words}" for status, words in STATUS_WORDS.items()
    )


def is_confirmed(path: Path) -> bool:
    """Show what a rebuild would lose, and ask before going ahead."""
    print(describe(path))
    print(
        "Rebuilding replaces it with a fresh copy of data/. Every decision, "
        "payment, sign-off and step in it is lost, and every claim goes back "
        "to waiting."
    )
    reply = input(f"Type {CONFIRMATION} to rebuild it: ")
    return reply.strip().lower() == CONFIRMATION


def rebuild(path: Path) -> Path:
    """Back up the database, then replace it with a fresh one. Return the backup."""
    backup = backup_path(path)
    shutil.copyfile(path, backup)
    build(path)
    return backup


def main() -> int:
    """Rebuild the database from data/, asking first if one exists."""
    path = database.path_from_environment()
    if not path.exists():
        build(path)
        print(f"Created {path} from data/, with every claim waiting")
        return 0
    if not is_confirmed(path):
        print("Nothing changed")
        return 1
    backup = rebuild(path)
    print(f"Rebuilt {path} with every claim waiting. The old one is in {backup}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
