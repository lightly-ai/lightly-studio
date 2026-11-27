"""Reads a streamed chat completion of OpenRouter.

A streamed completion arrives as server-sent events, one ``data: {json}`` line per chunk.
Each chunk holds a delta of the assistant message: a piece of the answer, a piece of the
reasoning, or pieces of tool calls. ``StreamAssembler`` joins the deltas into one message.
"""

from __future__ import annotations

from collections.abc import Iterable, Iterator, Mapping
from dataclasses import dataclass, field
from typing import Any

from lightly_studio.agent.chat_messages import (
    AgentMessage,
    AgentToolCall,
    AgentToolCallFunction,
    ContentDelta,
    ReasoningDelta,
)

ModelDelta = ReasoningDelta | ContentDelta

_DATA_PREFIX = "data:"
_DONE_DATA = "[DONE]"

# The fields of a reasoning block whose text arrives in pieces.
_JOINED_REASONING_FIELDS = ("text", "summary", "data")


class StreamAssembler:
    """Joins the deltas of a streamed completion into one assistant message."""

    def __init__(self) -> None:
        """Start with an empty message."""
        self._content: list[str] = []
        self._reasoning: list[str] = []
        self._tool_calls: dict[int, _ToolCallParts] = {}
        # A reasoning block is identified by its type and its index.
        self._reasoning_details: dict[tuple[str, int], dict[str, Any]] = {}

    def add_chunk(self, chunk: Mapping[str, Any]) -> list[ModelDelta]:
        """Add the delta of one chunk.

        Args:
            chunk: One parsed chunk of the stream.

        Returns:
            The new pieces of text that the GUI can show at once.
        """
        choices = chunk.get("choices") or []
        if not choices:
            return []
        delta: Mapping[str, Any] = choices[0].get("delta") or {}
        for part in delta.get("tool_calls") or []:
            self._add_tool_call_part(part=part)
        details: list[Mapping[str, Any]] = delta.get("reasoning_details") or []
        for detail in details:
            self._add_reasoning_detail(detail=detail)
        reasoning = delta.get("reasoning") or _summary_text(details=details)
        content = delta.get("content")
        deltas: list[ModelDelta] = []
        if reasoning:
            self._reasoning.append(reasoning)
            deltas.append(ReasoningDelta(text=reasoning))
        if content:
            self._content.append(content)
            deltas.append(ContentDelta(text=content))
        return deltas

    def message(self) -> AgentMessage:
        """Get the message that the added chunks make.

        Raises:
            ValueError: If a tool call has no ID or no function name.
        """
        return AgentMessage(
            role="assistant",
            content="".join(self._content) or None,
            reasoning="".join(self._reasoning) or None,
            reasoning_details=list(self._reasoning_details.values()) or None,
            tool_calls=[parts.to_tool_call() for _, parts in sorted(self._tool_calls.items())]
            or None,
        )

    def _add_tool_call_part(self, part: Mapping[str, Any]) -> None:
        """Join a piece of a tool call. The pieces of one call share its index."""
        parts = self._tool_calls.setdefault(part.get("index", 0), _ToolCallParts())
        function: Mapping[str, Any] = part.get("function") or {}
        # Some providers repeat the ID and the name in every piece, so only the first counts.
        parts.call_id = parts.call_id or part.get("id") or ""
        parts.name = parts.name or function.get("name") or ""
        parts.arguments.append(function.get("arguments") or "")

    def _add_reasoning_detail(self, detail: Mapping[str, Any]) -> None:
        """Join a piece of a reasoning block into the block of the same type and index."""
        key = (str(detail.get("type")), int(detail.get("index", len(self._reasoning_details))))
        block = self._reasoning_details.setdefault(key, {})
        for name, value in detail.items():
            if name in _JOINED_REASONING_FIELDS and isinstance(value, str):
                block[name] = block.get(name, "") + value
            elif value is not None:
                block[name] = value


def iter_event_data(lines: Iterable[str]) -> Iterator[str]:
    """Get the data of each server-sent event, until the end marker.

    Args:
        lines: The lines of the response body.

    Returns:
        An iterator over the data strings. Comments, such as the keep-alive comment
        ``: OPENROUTER PROCESSING``, and empty lines are left out.
    """
    for line in lines:
        if not line.startswith(_DATA_PREFIX):
            continue
        data = line[len(_DATA_PREFIX) :].strip()
        if data == _DONE_DATA:
            return
        if data:
            yield data


@dataclass
class _ToolCallParts:
    call_id: str = ""
    name: str = ""
    arguments: list[str] = field(default_factory=list)

    def to_tool_call(self) -> AgentToolCall:
        if not self.call_id or not self.name:
            raise ValueError("The model streamed a tool call without an ID or a name.")
        return AgentToolCall(
            id=self.call_id,
            function=AgentToolCallFunction(name=self.name, arguments="".join(self.arguments)),
        )


def _summary_text(details: Iterable[Mapping[str, Any]]) -> str:
    """Get the readable text of reasoning blocks. Encrypted blocks have none."""
    texts = (detail.get("text") or detail.get("summary") for detail in details)
    return "".join(text for text in texts if isinstance(text, str))
