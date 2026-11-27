"""Answer direct collection overview requests from the database."""

from __future__ import annotations

import json
import re
import uuid
from collections.abc import Iterator, Sequence

from lightly_studio.agent import overview_tool
from lightly_studio.agent.agent_events import AgentEvent, MessageEvent, TurnDoneEvent
from lightly_studio.agent.agent_tool import AgentContext
from lightly_studio.agent.chat_messages import AgentMessage, AgentToolCall, AgentToolCallFunction
from lightly_studio.agent.overview_tool import GetCollectionOverviewArgs

_OVERVIEW_STARTER = (
    "Give me a brief overview of this collection. Highlight what is worth exploring."
)
_REQUEST_PREFIX = re.compile(
    r"^(?:please )?(?:(?:give|show) me )?(?:(?:a|an|the) )?(?:brief )?", re.IGNORECASE
)
_OVERVIEW_REQUEST = re.compile(
    r"(?:(?:collection|dataset) (?:overview|summary|stats|statistics)"
    r"|(?:overview|summary|stats|statistics) (?:of|for) (?:this|the|my) (?:collection|dataset)"
    r"|summari[sz]e (?:this|the|my) (?:collection|dataset))[.!?]?",
    re.IGNORECASE,
)


def is_overview_request(history: Sequence[AgentMessage]) -> bool:
    """Recognize a request for the collection facts as a standalone task."""
    if not history or history[-1].role != "user":
        return False
    prompt = " ".join((history[-1].content or "").split())
    subject = _REQUEST_PREFIX.sub("", prompt, count=1)
    return prompt == _OVERVIEW_STARTER or _OVERVIEW_REQUEST.fullmatch(subject) is not None


def stream_overview(context: AgentContext) -> Iterator[AgentEvent]:
    """Stream the database facts as a complete turn that can be used in later prompts."""
    call = AgentToolCall(
        id=f"call_{uuid.uuid4().hex}",
        function=AgentToolCallFunction(
            name=overview_tool.GET_COLLECTION_OVERVIEW,
            arguments="{}",
        ),
    )
    yield MessageEvent(message=AgentMessage(role="assistant", tool_calls=[call]))
    overview = overview_tool.get_collection_overview(
        context=context, args=GetCollectionOverviewArgs()
    )
    yield MessageEvent(
        message=AgentMessage(role="tool", tool_call_id=call.id, content=json.dumps(overview))
    )
    image_count = overview["sample_count"]
    image_noun = "image" if image_count == 1 else "images"
    yield MessageEvent(
        message=AgentMessage(
            role="assistant",
            content=f"The collection has {image_count} {image_noun}.",
        )
    )
    yield TurnDoneEvent(ui_actions=[])
