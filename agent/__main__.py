"""Work the claims queue from the command line.

`uv run -m agent` works every waiting claim in queue order, and
`uv run -m agent CLM-1001` works one claim. It prints only each claim's id and
outcome, never a claim's details, which are personal data.
"""

import sys
from uuid import uuid4

import httpx
from pydantic import BaseModel, TypeAdapter

from agent import backend, main
from agent.main import Approval, Outcome, RunFailed

BACKEND_DOWN = "Start the backend with npm run dev"
HEALTHY = "ok"
WHAT_EACH_CHECK_READS = {
    "database": "its database",
    "policy_wording": "the policy wording",
    "instructions": "the agent's instructions",
}


class BackendUnhealthy(Exception):
    """The backend is running but can't serve claims."""


class Health(BaseModel):
    database: str
    policy_wording: str
    instructions: str


def check_backend() -> None:
    """Raise BackendUnhealthy, naming what the backend can't read, if a check fails."""
    checks = Health.model_validate_json(backend.health()).model_dump()
    unreadable = [
        WHAT_EACH_CHECK_READS[name]
        for name, result in checks.items()
        if result != HEALTHY
    ]
    if unreadable:
        raise BackendUnhealthy(
            f"The backend is running but can't read {' or '.join(unreadable)}"
        )


class QueuedClaim(BaseModel):
    claim_id: str
    status: str


def waiting_claims() -> list[str]:
    """Return the ids of the waiting claims, in queue order."""
    queue = TypeAdapter(list[QueuedClaim]).validate_json(backend.get("/api/claims"))
    return [claim.claim_id for claim in queue if claim.status == "waiting"]


def describe(outcome: Outcome) -> str:
    """Return the claim's id and outcome, such as `CLM-1001 approve $420.00`."""
    decision = outcome.decision
    if not isinstance(decision, Approval):
        return f"{outcome.claim_id} {decision.decision}"
    waiting = ", waiting for sign-off" if outcome.payment is None else ""
    return f"{outcome.claim_id} approve ${decision.payout:,.2f}{waiting}"


def work(claim_ids: list[str]) -> None:
    """Work each claim in turn, stopping at the first that fails."""
    for claim_id in claim_ids:
        try:
            outcome = main.run(claim_id, uuid4().hex)
        except Exception as error:
            error.add_note(f"The agent stopped while working {claim_id}")
            raise
        print(describe(outcome), flush=True)


def run_command(arguments: list[str]) -> int:
    """Work the claims named, or the waiting queue, and return the exit code."""
    try:
        check_backend()
        work(arguments or waiting_claims())
    except httpx.ConnectError:
        print(BACKEND_DOWN, file=sys.stderr)
        return 1
    except (BackendUnhealthy, RunFailed) as failure:
        print(failure, file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(run_command(sys.argv[1:]))
