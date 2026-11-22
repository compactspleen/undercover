"""The API's operations."""

import sqlite3
from collections.abc import Iterator
from contextlib import closing
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, Request
from fastapi.responses import PlainTextResponse

from backend import records
from backend.database import connect
from backend.models import Claim, ClaimHistory, ClaimSummary, Handler, Policy

POLICY_WORDING = Path(__file__).parent.parent / "data" / "policy_wording.md"

router = APIRouter(prefix="/api")


class MarkdownResponse(PlainTextResponse):
    media_type = "text/markdown"


def open_database(request: Request) -> Iterator[sqlite3.Connection]:
    """Open the database for one request."""
    with closing(connect(request.app.state.database_path)) as connection:
        yield connection


Database = Annotated[sqlite3.Connection, Depends(open_database)]


@router.get("/claims", operation_id="list_claims")
def list_claims(database: Database) -> list[ClaimSummary]:
    """List the claims queue in order, with each claim's status."""
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
