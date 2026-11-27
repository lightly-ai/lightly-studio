"""Agent tools that list and run the registered operators.

Operators are plugins that register at startup, so the agent finds them at run time. Each
operator describes itself and its parameters, and the agent passes that description to the
model.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from pydantic import BaseModel, Field

from lightly_studio.agent import sample_source
from lightly_studio.agent.agent_tool import AgentContext, AgentTool
from lightly_studio.agent.ui_actions import RefreshDataAction
from lightly_studio.plugins.base_operator import BaseOperator
from lightly_studio.plugins.operator_context import ExecutionContext
from lightly_studio.plugins.parameter import BaseParameter, FloatParameter
from lightly_studio.resolvers.sample_resolver.sample_filter import SampleFilter
from lightly_studio.services import operator_service


class ListOperatorsArgs(BaseModel):
    """The list takes no arguments."""


class RunOperatorArgs(BaseModel):
    """Arguments of ``run_operator``."""

    operator_name: str = Field(
        min_length=1, description="The name of the operator, as list_operators gives it."
    )
    parameters: dict[str, Any] = Field(
        default_factory=dict,
        description=(
            "The parameter values by parameter name. A parameter that is left out takes its "
            "default value."
        ),
    )
    source: str | None = Field(
        default=None,
        description=(
            "Optional. Run the operator only on these samples. Without it, the operator "
            "runs on the whole collection. " + sample_source.SOURCE_DESCRIPTION
        ),
    )


def list_operators(context: AgentContext, args: ListOperatorsArgs) -> dict[str, Any]:
    """List the operators that can run on the collection, with their parameters."""
    del args
    operators = [
        operator
        for operator in _get_operators(context=context)
        if operator_service.get_scope_error(operator=operator, collection=context.collection)
        is None
    ]
    return {
        "operators": [
            {
                "name": operator.name,
                "description": operator.description,
                "status": operator.status.value,
                "parameters": [
                    operator_service.to_parameter_view(parameter=parameter).model_dump(
                        mode="json", exclude_none=True
                    )
                    for parameter in operator.parameters
                ],
            }
            for operator in operators
        ]
    }


def run_operator(context: AgentContext, args: RunOperatorArgs) -> dict[str, Any]:
    """Run an operator on the collection or on some of its samples."""
    operator = _get_operator_by_name(context=context, name=args.operator_name.strip())
    error = operator_service.get_status_error(
        operator=operator, operator_ref=operator.name
    ) or operator_service.get_scope_error(operator=operator, collection=context.collection)
    if error is not None:
        raise ValueError(error)
    parameters = _get_parameter_values(parameters=operator.parameters, values=args.parameters)
    context_filter = (
        None
        if args.source is None
        else SampleFilter(sample_ids=sample_source.resolve_source(context, args.source))
    )
    result = operator.execute(
        session=context.session,
        context=ExecutionContext(
            collection_id=context.collection.collection_id, context_filter=context_filter
        ),
        parameters=parameters,
    )
    # The operator can change annotations, tags or metadata that the GUI shows.
    context.ui_actions.append(RefreshDataAction())
    return {"operator": operator.name, "success": result.success, "message": result.message}


OPERATOR_TOOLS: list[AgentTool[Any]] = [
    AgentTool(
        name="list_operators",
        description=(
            "List the operators that can run on this collection: plugins such as "
            "auto-labeling, inference or training. Gives the name, the description, the "
            "status and the parameters of each operator. Call it before run_operator."
        ),
        args_model=ListOperatorsArgs,
        run=list_operators,
    ),
    AgentTool(
        name="run_operator",
        description=(
            "Run an operator from list_operators on the collection, or only on some samples. "
            "Returns whether it succeeded and its message. The GUI then reloads the data."
        ),
        args_model=RunOperatorArgs,
        run=run_operator,
    ),
]


def _get_operators(context: AgentContext) -> list[BaseOperator]:
    registry = context.operator_registry
    operators = (
        registry.get_by_id(operator_id=metadata.operator_id)
        for metadata in registry.get_all_metadata()
    )
    return [operator for operator in operators if operator is not None]


def _get_operator_by_name(context: AgentContext, name: str) -> BaseOperator:
    """Find the one operator with the name.

    Raises:
        ValueError: If no operator or several operators have the name.
    """
    matches = [operator for operator in _get_operators(context=context) if operator.name == name]
    if len(matches) != 1:
        problem = "no operator" if not matches else "several operators"
        raise ValueError(f"There is {problem} named {name!r}. Call list_operators.")
    return matches[0]


def _get_parameter_values(
    parameters: list[BaseParameter], values: Mapping[str, Any]
) -> dict[str, Any]:
    """Check the values against the parameters of the operator, and add the defaults.

    Raises:
        ValueError: If a value has no parameter, a required value is missing, or a value
            has the wrong type.
    """
    names = {parameter.name for parameter in parameters}
    unknown = sorted(set(values) - names)
    if unknown:
        raise ValueError(f"Unknown parameters {unknown}. The parameters are {sorted(names)}.")
    checked: dict[str, Any] = {}
    for parameter in parameters:
        if parameter.name in values:
            checked[parameter.name] = _check_value(
                parameter=parameter, value=values[parameter.name]
            )
        elif parameter.default is not None:
            checked[parameter.name] = parameter.default
        elif parameter.required:
            raise ValueError(f"The parameter {parameter.name!r} is required.")
    return checked


def _check_value(parameter: BaseParameter, value: Any) -> Any:
    # A model can write a whole number such as 1 for a float parameter.
    if isinstance(parameter, FloatParameter) and type(value) is int:
        value = float(value)
    try:
        # The parameter classes check a value only in this private method.
        return parameter._validate(value)  # noqa: SLF001
    except (TypeError, ValueError) as exc:
        raise ValueError(f"The parameter {parameter.name!r} is not valid: {exc}") from exc
