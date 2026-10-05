from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import pytest
from sqlmodel import Session

from lightly_studio.agent import operator_tools
from lightly_studio.agent.agent_tool import AgentContext
from lightly_studio.agent.operator_tools import ListOperatorsArgs, RunOperatorArgs
from lightly_studio.agent.ui_actions import RefreshDataAction
from lightly_studio.plugins.base_operator import BaseOperator, OperatorResult, OperatorStatus
from lightly_studio.plugins.operator_context import ExecutionContext, OperatorScope
from lightly_studio.plugins.operator_registry import OperatorRegistry
from lightly_studio.plugins.parameter import BaseParameter, FloatParameter, StringParameter
from lightly_studio.resolvers.sample_resolver.sample_filter import SampleFilter
from tests.agent import helpers_agent

_EMBEDDINGS = {"a.jpg": [1.0, 0.0], "b.jpg": [0.0, 1.0]}


def test_list_operators(db_session: Session) -> None:
    context, _, _ = _create_context(session=db_session)

    result = operator_tools.list_operators(context, ListOperatorsArgs())

    # The video operator cannot run on an image collection, so the list leaves it out.
    assert result == {
        "operators": [
            {
                "name": "auto-label",
                "description": "Labels images.",
                "status": "ready",
                "parameters": [
                    {
                        "name": "prompt",
                        "description": "What to label.",
                        "required": True,
                        "param_type": "str",
                    },
                    {
                        "name": "threshold",
                        "description": "",
                        "default": 0.5,
                        "required": False,
                        "param_type": "float",
                    },
                ],
            }
        ]
    }


def test_run_operator(db_session: Session) -> None:
    context, operator, ids = _create_context(session=db_session, selected_file_names=["b.jpg"])

    result = operator_tools.run_operator(
        context,
        RunOperatorArgs(
            operator_name="auto-label", parameters={"prompt": "car"}, source="selection"
        ),
    )

    assert result == {"operator": "auto-label", "success": True, "message": "labeled car"}
    assert operator.calls == [
        (
            ExecutionContext(
                collection_id=context.collection.collection_id,
                context_filter=SampleFilter(sample_ids=[ids["b.jpg"]]),
            ),
            {"prompt": "car", "threshold": 0.5},
        )
    ]
    assert context.ui_actions == [RefreshDataAction()]


def test_run_operator__whole_number_for_float(db_session: Session) -> None:
    context, operator, _ = _create_context(session=db_session)

    operator_tools.run_operator(
        context,
        RunOperatorArgs(operator_name="auto-label", parameters={"prompt": "car", "threshold": 1}),
    )

    assert operator.calls[0][0].context_filter is None
    assert operator.calls[0][1] == {"prompt": "car", "threshold": 1.0}


@pytest.mark.parametrize(
    ("parameters", "message"),
    [
        ({"prompt": "car", "color": "red"}, r"Unknown parameters \['color'\]"),
        ({}, "'prompt' is required"),
        ({"prompt": 3}, "'prompt' is not valid"),
    ],
)
def test_run_operator__invalid_parameters(
    db_session: Session, parameters: dict[str, Any], message: str
) -> None:
    context, operator, _ = _create_context(session=db_session)

    with pytest.raises(ValueError, match=message):
        operator_tools.run_operator(
            context, RunOperatorArgs(operator_name="auto-label", parameters=parameters)
        )
    assert operator.calls == []


def test_run_operator__unknown_name(db_session: Session) -> None:
    context, _, _ = _create_context(session=db_session)

    with pytest.raises(ValueError, match="no operator named 'segment'"):
        operator_tools.run_operator(context, RunOperatorArgs(operator_name="segment"))


def test_run_operator__not_ready(db_session: Session) -> None:
    context, operator, _ = _create_context(session=db_session)
    operator.status = OperatorStatus.STARTING

    with pytest.raises(ValueError, match="'auto-label' is still starting"):
        operator_tools.run_operator(
            context, RunOperatorArgs(operator_name="auto-label", parameters={"prompt": "car"})
        )


def test_run_operator__wrong_scope(db_session: Session) -> None:
    context, _, _ = _create_context(session=db_session)

    with pytest.raises(ValueError, match="cannot be executed in this context"):
        operator_tools.run_operator(context, RunOperatorArgs(operator_name="track"))


@dataclass
class _AutoLabelOperator(BaseOperator):
    """An image operator that records its calls."""

    name: str = "auto-label"
    description: str = "Labels images."
    status: OperatorStatus = OperatorStatus.READY
    calls: list[tuple[ExecutionContext, dict[str, Any]]] = field(default_factory=list)

    @property
    def parameters(self) -> list[BaseParameter]:
        return [
            StringParameter(name="prompt", description="What to label."),
            FloatParameter(name="threshold", default=0.5, required=False),
        ]

    @property
    def supported_scopes(self) -> list[OperatorScope]:
        return [OperatorScope.IMAGE]

    def execute(
        self, session: Session, context: ExecutionContext, parameters: dict[str, Any]
    ) -> OperatorResult:
        del session
        self.calls.append((context, parameters))
        return OperatorResult(success=True, message=f"labeled {parameters['prompt']}")


@dataclass
class _VideoOperator(BaseOperator):
    name: str = "track"
    description: str = "Tracks objects in videos."
    status: OperatorStatus = OperatorStatus.READY

    @property
    def parameters(self) -> list[BaseParameter]:
        return []

    @property
    def supported_scopes(self) -> list[OperatorScope]:
        return [OperatorScope.VIDEO]

    def execute(
        self, session: Session, context: ExecutionContext, parameters: dict[str, Any]
    ) -> OperatorResult:
        del session, context, parameters
        raise AssertionError("The video operator must not run on images.")


def _create_context(
    session: Session, selected_file_names: tuple[str, ...] | list[str] = ()
) -> tuple[AgentContext, _AutoLabelOperator, dict[str, Any]]:
    collection, ids = helpers_agent.create_collection_with_embeddings(
        session=session, embeddings_by_file=_EMBEDDINGS
    )
    operator = _AutoLabelOperator()
    registry = OperatorRegistry()
    registry.register(operator=operator)
    registry.register(operator=_VideoOperator())
    context = helpers_agent.create_context(
        session=session,
        collection=collection,
        selected_sample_ids=[ids[file_name] for file_name in selected_file_names],
        operator_registry=registry,
    )
    return context, operator, ids
