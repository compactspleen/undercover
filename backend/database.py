"""The SQLite database: its tables, and how to open it."""

import os
import sqlite3
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path

DEFAULT_PATH = Path(__file__).parent.parent / "undercover.db"

# Money is stored in whole cents, so sums and comparisons are exact.
sqlite3.register_adapter(Decimal, lambda amount: int(amount.scaleb(2)))
sqlite3.register_adapter(date, date.isoformat)
sqlite3.register_adapter(datetime, datetime.isoformat)
sqlite3.register_converter("CENTS", lambda value: Decimal(int(value)).scaleb(-2))
sqlite3.register_converter("DATE", lambda value: date.fromisoformat(value.decode()))
sqlite3.register_converter(
    "TIMESTAMP", lambda value: datetime.fromisoformat(value.decode())
)

SCHEMA = """
CREATE TABLE company (payout_approval_limit CENTS NOT NULL);
CREATE TABLE handlers (
    handler_id TEXT PRIMARY KEY, name TEXT NOT NULL, role TEXT NOT NULL
);
CREATE TABLE plans (
    plan TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    trip_cancellation_max CENTS NOT NULL,
    trip_delay_waiting_hours INTEGER NOT NULL,
    trip_delay_max CENTS NOT NULL,
    baggage_delay_waiting_hours INTEGER NOT NULL,
    baggage_delay_max CENTS NOT NULL,
    baggage_max CENTS NOT NULL,
    per_item_limit CENTS NOT NULL,
    passport_max CENTS NOT NULL,
    emergency_medical_max CENTS NOT NULL,
    deductible CENTS NOT NULL
);
CREATE TABLE add_ons (
    add_on TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    effect TEXT NOT NULL,
    electronics_per_item_limit CENTS
);
CREATE TABLE deductible_claim_types (claim_type TEXT PRIMARY KEY);
CREATE TABLE customers (
    customer_id TEXT PRIMARY KEY, name TEXT NOT NULL, customer_since DATE NOT NULL
);
CREATE TABLE previous_claims (
    customer_id TEXT NOT NULL REFERENCES customers,
    claim_id TEXT NOT NULL,
    filed_on DATE NOT NULL,
    incident_date DATE NOT NULL,
    claim_type TEXT NOT NULL,
    summary TEXT NOT NULL,
    outcome TEXT NOT NULL,
    amount_paid CENTS NOT NULL
);
CREATE TABLE policies (
    policy_id TEXT PRIMARY KEY,
    customer_id TEXT NOT NULL REFERENCES customers,
    plan TEXT NOT NULL REFERENCES plans,
    purchased_on DATE NOT NULL,
    sold_through TEXT NOT NULL,
    destination TEXT NOT NULL,
    departs_on DATE NOT NULL,
    returns_on DATE NOT NULL,
    trip_cost CENTS NOT NULL,
    status TEXT NOT NULL
);
CREATE TABLE policy_add_ons (
    policy_id TEXT NOT NULL REFERENCES policies,
    add_on TEXT NOT NULL REFERENCES add_ons
);
CREATE TABLE travelers (
    policy_id TEXT NOT NULL REFERENCES policies, name TEXT NOT NULL
);
CREATE TABLE claims (
    claim_id TEXT PRIMARY KEY,
    policy_id TEXT NOT NULL REFERENCES policies,
    customer_id TEXT NOT NULL REFERENCES customers,
    claim_type TEXT NOT NULL,
    submitted_on DATE NOT NULL,
    incident_date DATE NOT NULL,
    incident_location TEXT NOT NULL,
    summary TEXT NOT NULL,
    story TEXT NOT NULL,
    amount_claimed CENTS NOT NULL,
    status TEXT NOT NULL
);
CREATE TABLE items (
    claim_id TEXT NOT NULL REFERENCES claims,
    description TEXT NOT NULL,
    category TEXT NOT NULL,
    amount CENTS NOT NULL
);
CREATE TABLE documents (
    claim_id TEXT NOT NULL REFERENCES claims,
    name TEXT NOT NULL,
    type TEXT NOT NULL,
    content TEXT NOT NULL
);
CREATE TABLE decisions (
    claim_id TEXT PRIMARY KEY REFERENCES claims,
    decision TEXT NOT NULL,
    payout CENTS,
    explanation TEXT NOT NULL,
    policy_section TEXT NOT NULL
);
CREATE TABLE payments (
    claim_id TEXT PRIMARY KEY REFERENCES claims,
    amount CENTS NOT NULL,
    paid_at TIMESTAMP NOT NULL
);
CREATE TABLE sign_offs (
    claim_id TEXT PRIMARY KEY REFERENCES claims,
    handler_id TEXT NOT NULL REFERENCES handlers,
    signed_off_at TIMESTAMP NOT NULL
);
CREATE TABLE steps (
    claim_id TEXT NOT NULL REFERENCES claims,
    kind TEXT NOT NULL,
    text TEXT NOT NULL,
    recorded_at TIMESTAMP NOT NULL
);
"""


def path_from_environment() -> Path:
    """Return the database file named in UNDERCOVER_DB, or the default."""
    return Path(os.environ.get("UNDERCOVER_DB") or DEFAULT_PATH)


def as_dict(cursor: sqlite3.Cursor, row: tuple[object, ...]) -> dict[str, object]:
    """Turn a row into a dict keyed by column name."""
    return {
        column[0]: value for column, value in zip(cursor.description, row, strict=True)
    }


def connect(path: Path) -> sqlite3.Connection:
    """Open the database, with each write in a transaction of its own."""
    connection = sqlite3.connect(
        path,
        detect_types=sqlite3.PARSE_DECLTYPES,
        isolation_level=None,
        check_same_thread=False,
    )
    connection.row_factory = as_dict
    return connection
