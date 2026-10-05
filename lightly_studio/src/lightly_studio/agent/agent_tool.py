"""The shape of one agent tool, and the context that every tool gets."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any, Generic, TypeVar
from uuid import UUID

from pydantic import BaseModel
from sqlmodel import Session

from lightly_studio.agent.result_store import ResultStore
from lightly_studio.agent.ui_actions import UiAction
from lightly_studio.models.collection import CollectionTable

ArgsT = TypeVar("ArgsT", bound=BaseModel)


@dataclass
class AgentContext:
    """What a tool can read and change during one agent turn.

    Attributes:
        session: The database session of the request.
        collection: The collection that the chat is about.
        selected_sample_ids: The samples that the user selected in the GUI.
        result_store: The store of the result handles.
        ui_actions: The actions for the GUI. Tools append to it.
    """

    session: Session
    collection: CollectionTable
    selected_sample_ids: list[UUID]
    result_store: ResultStore
    ui_actions: list[UiAction] = field(default_factory=list)


@dataclass(frozen=True)
class AgentTool(Generic[ArgsT]):
    """One function that the model can call.

    The arguments are a Pydantic model. Its JSON schema tells the model what to send, and
    its validation parses what the model sent.

    Attributes:
        name: The function name that the model calls.
        description: What the tool does, for the model.
        args_model: The model of the arguments.
        run: Runs the tool and returns a JSON-serializable result for the model. It raises
            ``ValueError`` for a request that it cannot do.
    """

    name: str
    description: str
    args_model: type[ArgsT]
    run: Callable[[AgentContext, ArgsT], dict[str, Any]]

    def definition(self) -> dict[str, Any]:
        """Get the tool definition in the OpenAI ``tools`` format."""
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.args_model.model_json_schema(),
            },
        }

    def run_json(self, context: AgentContext, arguments: str) -> dict[str, Any]:
        """Parse the JSON arguments of the model and run the tool.

        Args:
            context: The context of the turn.
            arguments: The arguments as the model wrote them. An empty string means no
                arguments.

        Returns:
            The result for the model.

        Raises:
            pydantic.ValidationError: If the arguments do not match ``args_model``.
            ValueError: If the tool cannot do the request.
        """
        args = self.args_model.model_validate_json(arguments or "{}")
        return self.run(context, args)
