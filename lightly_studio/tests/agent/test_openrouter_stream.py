from __future__ import annotations

from typing import Any

import pytest

from lightly_studio.agent import openrouter_stream
from lightly_studio.agent.chat_messages import ContentDelta, ReasoningDelta
from lightly_studio.agent.openrouter_stream import StreamAssembler


class TestStreamAssembler:
    def test_add_chunk__text(self) -> None:
        assembler = StreamAssembler()

        first = assembler.add_chunk(chunk=_chunk(delta={"reasoning": "Think", "content": "Hel"}))
        second = assembler.add_chunk(chunk=_chunk(delta={"content": "lo"}))

        assert first == [ReasoningDelta(text="Think"), ContentDelta(text="Hel")]
        assert second == [ContentDelta(text="lo")]
        message = assembler.message()
        assert message.role == "assistant"
        assert message.content == "Hello"
        assert message.reasoning == "Think"
        assert message.tool_calls is None
        assert message.reasoning_details is None

    def test_add_chunk__no_choices(self) -> None:
        assembler = StreamAssembler()

        # The last chunk of a stream can carry only the token usage.
        deltas = assembler.add_chunk(chunk={"choices": [], "usage": {"total_tokens": 3}})

        assert deltas == []
        assert assembler.message().content is None

    def test_add_chunk__tool_calls_in_pieces(self) -> None:
        assembler = StreamAssembler()
        pieces: list[dict[str, Any]] = [
            {"index": 1, "id": "call_b", "function": {"name": "g", "arguments": ""}},
            {"index": 0, "id": "call_a", "function": {"name": "f", "arguments": '{"x"'}},
            # Some providers repeat the ID and the name in every piece.
            {"index": 0, "id": "call_a", "function": {"name": "f", "arguments": ": 1}"}},
            {"index": 1, "function": {"arguments": "{}"}},
        ]

        for piece in pieces:
            assert assembler.add_chunk(chunk=_chunk(delta={"tool_calls": [piece]})) == []

        tool_calls = assembler.message().tool_calls
        assert tool_calls is not None
        assert [(call.id, call.function.name, call.function.arguments) for call in tool_calls] == [
            ("call_a", "f", '{"x": 1}'),
            ("call_b", "g", "{}"),
        ]

    def test_add_chunk__reasoning_details(self) -> None:
        assembler = StreamAssembler()
        summary = {"type": "reasoning.summary", "index": 0, "format": "openai-responses-v1"}

        first = assembler.add_chunk(
            chunk=_chunk(delta={"reasoning_details": [{**summary, "summary": "Look "}]})
        )
        assembler.add_chunk(
            chunk=_chunk(delta={"reasoning_details": [{**summary, "summary": "first."}]})
        )
        assembler.add_chunk(
            chunk=_chunk(
                delta={
                    "reasoning_details": [
                        {"type": "reasoning.encrypted", "index": 0, "data": "c2VjcmV0"}
                    ]
                }
            )
        )

        # Without a `reasoning` field, the summary text is the reasoning text.
        assert first == [ReasoningDelta(text="Look ")]
        message = assembler.message()
        assert message.reasoning == "Look first."
        assert message.reasoning_details == [
            {**summary, "summary": "Look first."},
            {"type": "reasoning.encrypted", "index": 0, "data": "c2VjcmV0"},
        ]

    def test_message__tool_call_without_name(self) -> None:
        assembler = StreamAssembler()
        assembler.add_chunk(
            chunk=_chunk(delta={"tool_calls": [{"index": 0, "function": {"arguments": "{}"}}]})
        )

        with pytest.raises(ValueError, match="without an ID or a name"):
            assembler.message()


def test_iter_event_data() -> None:
    lines = [
        ": OPENROUTER PROCESSING",
        "",
        'data: {"a": 1}',
        'data:{"b": 2}',
        "data: [DONE]",
        'data: {"c": 3}',
    ]

    assert list(openrouter_stream.iter_event_data(lines=lines)) == ['{"a": 1}', '{"b": 2}']


def _chunk(delta: dict[str, Any]) -> dict[str, Any]:
    return {"choices": [{"index": 0, "delta": delta}]}
