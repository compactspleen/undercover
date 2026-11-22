"""A chat model that gives scripted replies in place of a real model."""

from uuid import uuid4

from langchain_core.language_models.fake_chat_models import GenericFakeChatModel
from langchain_core.messages import AIMessage, BaseMessage
from langchain_core.outputs import ChatResult
from pydantic import Field


class StubModel(GenericFakeChatModel):
    prompts: list[list[BaseMessage]] = Field(default_factory=list)

    def bind_tools(self, tools, **kwargs):
        return self

    def _generate(self, messages, stop=None, run_manager=None, **kwargs) -> ChatResult:
        self.prompts.append(messages)
        return super()._generate(messages, stop, run_manager, **kwargs)


def call(name: str, **arguments: object) -> AIMessage:
    """A reply that calls one tool."""
    return AIMessage(
        content="", tool_calls=[{"name": name, "args": arguments, "id": uuid4().hex}]
    )


def stub(*replies: AIMessage) -> StubModel:
    return StubModel(messages=iter(replies))


def approval(claim_id: str, payout: float) -> AIMessage:
    return call(
        "record_decision",
        claim_id=claim_id,
        decision={
            "decision": "approve",
            "payout": payout,
            "explanation": "Your flight was canceled, so we cover your costs.",
            "policy_section": "3. Trip Delay",
        },
    )


def referral(claim_id: str) -> AIMessage:
    return call(
        "record_decision",
        claim_id=claim_id,
        decision={
            "decision": "refer",
            "explanation": "A handler will look at your claim.",
            "policy_section": "11. How to claim",
        },
    )
