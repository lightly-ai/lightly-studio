"""Runs one agent turn: the model calls tools until it can answer the user."""

from __future__ import annotations

import json
from collections.abc import Generator, Iterator, Sequence
from typing import Any

from lightly_studio.agent.agent_events import (
    AgentEvent,
    ContentDeltaEvent,
    MessageEvent,
    ReasoningDeltaEvent,
    TurnDoneEvent,
)
from lightly_studio.agent.agent_tool import AgentContext, AgentTool
from lightly_studio.agent.chat_messages import AgentMessage, AgentToolCall, ReasoningDelta
from lightly_studio.agent.distribution_tools import DISTRIBUTION_TOOLS
from lightly_studio.agent.docs_tools import DOCS_TOOLS
from lightly_studio.agent.filter_tools import FILTER_TOOLS
from lightly_studio.agent.openrouter_client import AgentLLMError, ChatModel
from lightly_studio.agent.operator_tools import OPERATOR_TOOLS
from lightly_studio.agent.overview_tool import OVERVIEW_TOOLS
from lightly_studio.agent.search_tools import SEARCH_TOOLS
from lightly_studio.agent.selection_tools import SELECTION_TOOLS
from lightly_studio.agent.suggestion_tools import SUGGEST_NEXT_STEPS, SUGGESTION_TOOLS
from lightly_studio.agent.tag_tools import TAG_TOOLS

AGENT_TOOLS: list[AgentTool[Any]] = [
    *OVERVIEW_TOOLS,
    *SEARCH_TOOLS,
    *FILTER_TOOLS,
    *DISTRIBUTION_TOOLS,
    *SELECTION_TOOLS,
    *TAG_TOOLS,
    *OPERATOR_TOOLS,
    *DOCS_TOOLS,
    *SUGGESTION_TOOLS,
]

# The largest number of model calls in one turn. It stops a model that calls tools in a loop.
MAX_STEPS = 16

_SYSTEM_PROMPT = """\
You are the assistant of LightlyStudio, a tool to curate image datasets. You work on the \
collection "{collection_name}". The user selected {selected_count} samples in the GUI.

Rules:
- Do the request with the tools. Do not ask for confirmation of a clear request.
- When the user picks a task without its details, for example "I want to select samples", \
ask one short question for the missing details. Suggest a default that fits the collection.
- Before you call tools, write one short sentence that tells the user your next step.
- Tools that find samples return an opaque result handle. Pass it to \
other tools. Never invent sample IDs or handles.
- If a result handle is unavailable, explain that the sample set needs to be found again.
- When the user asks for samples and a tag, first find the samples, then tag the handle.
- When the user asks for samples but no tag, show them with show_samples.
- When a request depends on the data, for example to choose selection strategies, call \
get_collection_overview first.
- To find samples by metadata values or annotation classes, use find_samples. To find them \
by what the images show, use search_by_text.
- When the user asks for samples that show an object, for example "images with clocks", and \
the annotation classes are not in this conversation yet, call list_annotation_classes first. \
When a class matches the object, also as a plural or a synonym, ask one short question: show \
the samples with annotations of that class, with its sample count, or search the image \
content with text search. This rule overrides the rule against confirmation questions. Do \
not ask when the user already said "annotated", "labeled" or "search". When no class \
matches, use search_by_text and do not ask.
- To count the samples per metadata value, per year of a date or per annotation class, use \
get_distribution. Do not call find_samples once per value.
- To select samples, use run_selection. Choose the strategies and their strengths from the \
request and from the overview. Combine strategies when the request names several goals.
- After a selection, compare each achieved distribution with its target. Tell the user when \
the selection did not reach a target.
- A typicality weighting needs typicality metadata. When the overview does not list it, \
compute it first with compute_metadata.
- A similarity strategy needs a query tag. To use the samples of a search as the query, tag \
them first with tag_samples.
- For a task that no other tool does, such as auto-labeling or inference, look for an \
operator with list_operators and run it with run_operator.
- To answer a question on how to use LightlyStudio, call search_docs and answer from its \
results. Give the URL of the page. When the docs do not answer the question, say so.
- When a tool returns an error, fix the call or explain the problem to the user.
- When the user asks who developed you or which model you are, say that you are the \
LightlyStudio assistant, developed by Lightly AI. Do not name the language model or its \
provider.
- Answer in one to three short sentences. Name the tag and the number of samples. An \
answer from the docs can have up to six short sentences or steps.
- Put the facts and results that answer the request in the final message text. Use plans and \
progress updates before tool calls. Include a call to suggest_next_steps with the written \
answer when it adds useful options. Avoid a separate step to generate suggestions. Suggest \
two or three steps that follow from the result and that your tools can do. After a \
search: tag the samples, find similar samples, or select diverse samples from them. After a \
tag: select from the tag, or show the class distribution of the tag. After a selection: tag \
it, or compare it with the target. After a docs answer: the task that the answer explains. \
When your answer is a question, the steps are the answer options, for example "Annotated \
clocks (12)" and "Text search for clocks". Each prompt is a complete request with real names \
and counts. Do not suggest the request that the user just made."""

# How to turn a selection request into strategies and their strengths. The model reads it
# together with the JSON schema of each strategy in run_selection.
_SELECTION_PLAYBOOK = """\
Selection playbook:
- When the user gives strategies or strengths, use them as given.
- "Diverse", "informative" or "to label first": diversity, strength 1.
- "Representative" or "typical": weights on typicality, strength 1. For "diverse but \
representative", use diversity 1 and weights on typicality 1.
- "Outliers", "edge cases" or "unusual": weights on typicality, strength -1, and diversity 1.
- "Without duplicates": deduplication. When the user gives no distance, use 0.1 and say so.
- "Like these samples" or "more of these": tag the samples, then similarity with that query \
tag, strength 2, and diversity 1 so that the selection does not repeat one sample.
- "Balanced over the classes" or "more of the rare classes": balance with "uniform", or with \
the shares that the user gives, strength 2, and diversity 1.
- "Balanced over" a metadata key, or shares for metadata values: one metadata_balance per \
key, strength 3, and diversity 1. A strength of 2 against diversity 1 can miss the target.
- "Diverse objects" or "focus on the objects": subpart_diversity, strength 1.
- When an achieved distribution misses its target by more than 0.1 and the user gave no \
strengths, tell the user and offer to run again with a higher balance strength.
"""


def stream_agent_turn(
    chat_model: ChatModel,
    context: AgentContext,
    history: Sequence[AgentMessage],
    tools: Sequence[AgentTool[Any]] = AGENT_TOOLS,
) -> Iterator[AgentEvent]:
    """Answer the last user message of the history, calling tools as the model asks.

    Args:
        chat_model: The language model.
        context: The context of the turn. The tools append their GUI actions to it.
        history: The transcript so far, ending with the new user message. System messages
            in it are dropped, because the server writes its own.
        tools: The tools that the model can call.

    Returns:
        An iterator over the events of the turn: the pieces of text while the model writes,
        each new message, and a ``TurnDoneEvent`` with the GUI actions last.

    Raises:
        AgentLLMError: If the model gives no usable answer.
    """
    tools_by_name = {tool.name: tool for tool in tools}
    definitions = [tool.definition() for tool in tools]
    conversation = [message for message in history if message.role != "system"]
    transcript = [_system_message(context=context)]
    transcript.extend(conversation)
    for _ in range(MAX_STEPS):
        reply = yield from _stream_reply(
            chat_model=chat_model, transcript=transcript, definitions=definitions
        )
        if not reply.tool_calls:
            _require_answer(reply=reply)
            yield MessageEvent(message=reply)
            yield TurnDoneEvent(ui_actions=context.ui_actions)
            return
        transcript.append(reply)
        yield MessageEvent(message=reply)
        for call in reply.tool_calls:
            tool_message = _run_tool_call(context=context, tools_by_name=tools_by_name, call=call)
            transcript.append(tool_message)
            yield MessageEvent(message=tool_message)
        if _uses_only_suggestions(reply=reply):
            if not (reply.content or "").strip():
                answer = yield from _stream_reply(
                    chat_model=chat_model, transcript=transcript, definitions=[]
                )
                _require_answer(reply=answer)
                yield MessageEvent(message=answer)
            yield TurnDoneEvent(ui_actions=context.ui_actions)
            return
    stop_message = AgentMessage(
        role="assistant", content=f"I stopped after {MAX_STEPS} steps without a final answer."
    )
    yield MessageEvent(message=stop_message)
    yield TurnDoneEvent(ui_actions=context.ui_actions)


def _system_message(context: AgentContext) -> AgentMessage:
    rules = _SYSTEM_PROMPT.format(
        collection_name=context.collection.name,
        selected_count=len(context.selected_sample_ids),
    )
    return AgentMessage(role="system", content=f"{rules}\n\n{_SELECTION_PLAYBOOK}")


def _uses_only_suggestions(reply: AgentMessage) -> bool:
    """Check whether all calls in this step suggest follow-up actions."""
    calls = reply.tool_calls or []
    return bool(calls) and all(call.function.name == SUGGEST_NEXT_STEPS for call in calls)


def _require_answer(reply: AgentMessage) -> None:
    if reply.tool_calls or not (reply.content or "").strip():
        raise AgentLLMError(
            "The agent finished without a written answer. Check the activity before sending again."
        )


def _stream_reply(
    chat_model: ChatModel,
    transcript: Sequence[AgentMessage],
    definitions: Sequence[dict[str, Any]],
) -> Generator[AgentEvent, None, AgentMessage]:
    """Stream one step of the model. Yield its pieces of text and return its message."""
    reply: AgentMessage | None = None
    for item in chat_model.stream(messages=transcript, tools=definitions):
        if isinstance(item, AgentMessage):
            reply = item
        elif isinstance(item, ReasoningDelta):
            yield ReasoningDeltaEvent(text=item.text)
        else:
            yield ContentDeltaEvent(text=item.text)
    if reply is None:
        raise AgentLLMError("The model stream ended without a message.")
    return reply.model_copy(update={"role": "assistant"})


def _run_tool_call(
    context: AgentContext, tools_by_name: dict[str, AgentTool[Any]], call: AgentToolCall
) -> AgentMessage:
    """Run one tool call. A failure becomes an error result, so the model can react."""
    tool = tools_by_name.get(call.function.name)
    if tool is None:
        result: dict[str, Any] = {"error": f"There is no tool named {call.function.name!r}."}
    else:
        try:
            result = tool.run_json(context=context, arguments=call.function.arguments)
        # A Pydantic `ValidationError` and every embedder error are `ValueError`s too.
        except ValueError as exc:
            result = {"error": str(exc)}
    return AgentMessage(role="tool", tool_call_id=call.id, content=json.dumps(result))
