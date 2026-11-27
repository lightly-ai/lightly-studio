"""The events of a streamed agent turn.

The server sends the events of a turn as they happen, one JSON object per line, so the GUI
can show the reasoning, the tool calls and their results while the agent works.
"""

from __future__ import annotations

from typing import Annotated, Literal

from pydantic import BaseModel, Field, RootModel

from lightly_studio.agent.chat_messages import AgentMessage
from lightly_studio.agent.ui_actions import UiAction


class ReasoningDeltaEvent(BaseModel):
    """A new piece of the reasoning of the current step."""

    type: Literal["reasoning_delta"] = "reasoning_delta"
    text: str


class ContentDeltaEvent(BaseModel):
    """A new piece of the text of the current step."""

    type: Literal["content_delta"] = "content_delta"
    text: str


class MessageEvent(BaseModel):
    """A complete new message of the transcript.

    An assistant message ends a step of the model, and replaces the deltas of that step. Its
    tool calls run next. A tool message is the result of one tool call.
    """

    type: Literal["message"] = "message"
    message: AgentMessage


class TurnDoneEvent(BaseModel):
    """The turn is complete. The GUI applies the actions in their order."""

    type: Literal["turn_done"] = "turn_done"
    ui_actions: list[UiAction]


class TurnErrorEvent(BaseModel):
    """The turn stopped because the language model gave no usable answer."""

    type: Literal["turn_error"] = "turn_error"
    detail: str


AgentEvent = Annotated[
    ReasoningDeltaEvent | ContentDeltaEvent | MessageEvent | TurnDoneEvent | TurnErrorEvent,
    Field(discriminator="type"),
]


class AgentStreamLine(RootModel[AgentEvent]):
    """One line of a streamed agent turn: one event as JSON."""
