"""Chat messages in the OpenAI-compatible format that OpenRouter speaks.

The GUI keeps the full transcript, including the tool calls and the tool results, and sends
it back with each request. The server therefore holds no chat state, and the model still
sees the result handles of earlier turns.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel


class AgentToolCallFunction(BaseModel):
    """The function part of a tool call."""

    name: str
    arguments: str
    """The arguments as a JSON string, as the model wrote them."""


class AgentToolCall(BaseModel):
    """One tool call that the model asks for."""

    id: str
    type: Literal["function"] = "function"
    function: AgentToolCallFunction


class AgentMessage(BaseModel):
    """One message of the chat transcript."""

    role: Literal["system", "user", "assistant", "tool"]
    content: str | None = None
    tool_calls: list[AgentToolCall] | None = None
    tool_call_id: str | None = None
    """For a message with role ``tool``: the ID of the call that it answers."""
