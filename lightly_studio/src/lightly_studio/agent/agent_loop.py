"""Runs one agent turn: the model calls tools until it can answer the user."""

from __future__ import annotations

import json
from collections.abc import Sequence
from typing import Any

from pydantic import BaseModel

from lightly_studio.agent.agent_tool import AgentContext, AgentTool
from lightly_studio.agent.chat_messages import AgentMessage, AgentToolCall
from lightly_studio.agent.openrouter_client import ChatModel
from lightly_studio.agent.search_tools import SEARCH_TOOLS
from lightly_studio.agent.tag_tools import TAG_TOOLS
from lightly_studio.agent.ui_actions import UiAction

AGENT_TOOLS: list[AgentTool[Any]] = [*SEARCH_TOOLS, *TAG_TOOLS]

# The largest number of model calls in one turn. It stops a model that calls tools in a loop.
MAX_STEPS = 8

_SYSTEM_PROMPT = """\
You are the assistant of LightlyStudio, a tool to curate image datasets. You work on the \
collection "{collection_name}". The user selected {selected_count} samples in the GUI.

Rules:
- Do the request with the tools. Do not ask for confirmation of a clear request.
- Tools that find samples return a result handle such as "result_3". Pass the handle to \
other tools. Never invent sample IDs or handles.
- When the user asks for samples and a tag, first find the samples, then tag the handle.
- When the user asks for samples but no tag, show them with show_samples.
- When a tool returns an error, fix the call or explain the problem to the user.
- Answer in one to three short sentences. Name the tag and the number of samples."""


class AgentTurnResult(BaseModel):
    """The result of one agent turn.

    Attributes:
        messages: The messages that the turn added to the transcript, in order. The last
            one is the answer of the assistant.
        ui_actions: The actions for the GUI, in the order that the tools recorded them.
    """

    messages: list[AgentMessage]
    ui_actions: list[UiAction]


def run_agent_turn(
    chat_model: ChatModel,
    context: AgentContext,
    history: Sequence[AgentMessage],
    tools: Sequence[AgentTool[Any]] = AGENT_TOOLS,
) -> AgentTurnResult:
    """Answer the last user message of the history, calling tools as the model asks.

    Args:
        chat_model: The language model.
        context: The context of the turn. The tools append their GUI actions to it.
        history: The transcript so far, ending with the new user message. System messages
            in it are dropped, because the server writes its own.
        tools: The tools that the model can call.

    Returns:
        The new messages and the GUI actions.

    Raises:
        AgentLLMError: If the model gives no usable answer.
    """
    tools_by_name = {tool.name: tool for tool in tools}
    definitions = [tool.definition() for tool in tools]
    transcript = [_system_message(context=context)]
    transcript.extend(message for message in history if message.role != "system")
    new_messages: list[AgentMessage] = []
    for _ in range(MAX_STEPS):
        reply = chat_model.complete(messages=transcript, tools=definitions)
        reply = reply.model_copy(update={"role": "assistant"})
        transcript.append(reply)
        new_messages.append(reply)
        if not reply.tool_calls:
            return AgentTurnResult(messages=new_messages, ui_actions=context.ui_actions)
        for call in reply.tool_calls:
            tool_message = _run_tool_call(context=context, tools_by_name=tools_by_name, call=call)
            transcript.append(tool_message)
            new_messages.append(tool_message)
    new_messages.append(
        AgentMessage(
            role="assistant",
            content=f"I stopped after {MAX_STEPS} steps without a final answer.",
        )
    )
    return AgentTurnResult(messages=new_messages, ui_actions=context.ui_actions)


def _system_message(context: AgentContext) -> AgentMessage:
    return AgentMessage(
        role="system",
        content=_SYSTEM_PROMPT.format(
            collection_name=context.collection.name,
            selected_count=len(context.selected_sample_ids),
        ),
    )


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
