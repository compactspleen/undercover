"""The UnderCover Agent."""

import json
import os
from collections.abc import Iterable, Iterator
from decimal import Decimal
from enum import StrEnum
from typing import Annotated, Literal

from dotenv import load_dotenv
from langchain.agents import create_agent
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage, ToolMessage
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field, SecretStr

from agent import backend
from agent.tools import TOOLS

load_dotenv(override=True)

OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
DEFAULT_MODEL = "openai/gpt-6-luna"
RESULT_SUMMARY_LENGTH = 200


class StepKind(StrEnum):
    TOOL_CALL = "tool_call"
    TOOL_RESULT = "tool_result"
    REPLY = "reply"


class Approval(BaseModel):
    decision: Literal["approve"]
    payout: Decimal


class Rejection(BaseModel):
    decision: Literal["decline", "refer"]


class Payment(BaseModel):
    amount: Decimal


DecisionMade = Annotated[Approval | Rejection, Field(discriminator="decision")]


class ClaimState(BaseModel):
    """Where a claim stands, as the backend reports it."""

    claim_id: str
    status: str
    decision: DecisionMade | None
    payment: Payment | None


class Outcome(BaseModel):
    """Where a claim stands after a run that decided it."""

    claim_id: str
    status: str
    decision: DecisionMade
    payment: Payment | None


class RunFailed(Exception):
    """The agent finished a claim without completing it."""


def model() -> ChatOpenAI:
    """Return the model named in MODEL_NAME, or GPT-6 Luna by default."""
    name = os.getenv("MODEL_NAME")
    return ChatOpenAI(
        model=name or DEFAULT_MODEL,
        base_url=OPENROUTER_BASE_URL,
        api_key=SecretStr(os.environ["OPENROUTER_API_KEY"]),
        reasoning_effort=None if name else "low",
    )


def run(claim_id: str, thread_id: str, llm: BaseChatModel | None = None) -> Outcome:
    """Work one claim, recording each step, and return its outcome."""
    instructions = backend.get("/api/instructions")
    backend.post(f"/api/claims/{claim_id}/start", {})
    agent = create_agent(llm or model(), tools=TOOLS, system_prompt=instructions)
    updates = agent.stream(
        {"messages": [{"role": "user", "content": f"Work claim {claim_id}."}]},
        config={"configurable": {"thread_id": thread_id}},
        stream_mode="updates",
    )
    for message in new_messages(updates):
        for step in steps_for(message):
            backend.post(f"/api/claims/{claim_id}/steps", step)
    return checked(
        ClaimState.model_validate_json(backend.get(f"/api/claims/{claim_id}"))
    )


def new_messages(
    updates: Iterable[dict[str, dict[str, list[BaseMessage]]]],
) -> Iterator[BaseMessage]:
    """Yield each message the agent adds, as it adds it."""
    for update in updates:
        for output in update.values():
            yield from output["messages"]


def steps_for(message: BaseMessage) -> list[dict[str, object]]:
    """Return the steps that show a handler what this message did."""
    if isinstance(message, ToolMessage):
        return [step(StepKind.TOOL_RESULT, f"{message.name}: {summary(message.text)}")]
    if isinstance(message, AIMessage) and message.tool_calls:
        return [
            step(StepKind.TOOL_CALL, f"{call['name']} {json.dumps(call['args'])}")
            for call in message.tool_calls
        ]
    return [step(StepKind.REPLY, message.text)] if message.text else []


def step(kind: StepKind, text: str) -> dict[str, object]:
    return {"kind": kind, "text": text}


def summary(text: str) -> str:
    """Shorten a tool result to its opening."""
    if len(text) <= RESULT_SUMMARY_LENGTH:
        return text
    return f"{text[:RESULT_SUMMARY_LENGTH]}…"


def checked(state: ClaimState) -> Outcome:
    """Return the claim's outcome, or raise RunFailed if it was left unfinished."""
    if state.decision is None:
        raise RunFailed(f"{state.claim_id}: the run ended without a decision")
    outcome = Outcome.model_validate(state.model_dump())
    if (
        isinstance(outcome.decision, Approval)
        and outcome.status == "decided"
        and outcome.payment is None
    ):
        raise RunFailed(f"{outcome.claim_id}: approved but not paid")
    return outcome
