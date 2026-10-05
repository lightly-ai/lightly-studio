"""Checks whether a registered operator can run, and describes its parameters.

The operator API routes and the agent tools share these functions.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel

from lightly_studio.models.collection import CollectionTable
from lightly_studio.plugins import operator_context
from lightly_studio.plugins.base_operator import BaseOperator, OperatorStatus
from lightly_studio.plugins.parameter import BaseParameter, TableParameter


class ParameterColumnView(BaseModel):
    """A single column of a table parameter as exposed to the GUI."""

    name: str
    description: str
    default: Any = None
    required: bool
    param_type: str | None


class ParameterView(ParameterColumnView):
    """An operator parameter as exposed to the GUI."""

    columns: list[ParameterColumnView] | None = None
    """The columns of a table parameter, `None` for every other parameter type."""


def get_status_error(operator: BaseOperator, operator_ref: str) -> str | None:
    """Get the reason why the status of an operator does not let it run.

    Args:
        operator: The operator.
        operator_ref: How the message names the operator, for example its ID.

    Returns:
        The reason, or ``None`` if the operator is ready.
    """
    if operator.status == OperatorStatus.READY:
        return None
    if operator.status in (OperatorStatus.PENDING, OperatorStatus.STARTING):
        return f"Operator '{operator_ref}' is still starting, please try again in a moment."
    if operator.status in (OperatorStatus.STOPPING, OperatorStatus.STOPPED):
        return f"Operator '{operator_ref}' has been stopped and cannot be executed."
    return f"Operator '{operator_ref}' is in an error state and cannot be executed."


def get_scope_error(operator: BaseOperator, collection: CollectionTable) -> str | None:
    """Get the reason why an operator cannot run on a collection.

    Args:
        operator: The operator.
        collection: The collection to run the operator on.

    Returns:
        The reason, or ``None`` if the operator supports a scope of the collection.
    """
    collection_scopes = operator_context.get_allowed_scopes_for_collection(
        sample_type=collection.sample_type,
        is_root_collection=collection.parent_collection_id is None,
    )
    if any(scope in operator.supported_scopes for scope in collection_scopes):
        return None
    supported = ", ".join(scope.value for scope in operator.supported_scopes)
    return (
        f"Operator '{operator.name}' cannot be executed in this context. "
        f"Supported scopes: {supported}."
    )


def to_parameter_view(parameter: BaseParameter) -> ParameterView:
    """Convert an operator parameter into its API representation.

    Args:
        parameter: The parameter as declared by the operator.

    Returns:
        The parameter as exposed to the GUI, with the columns filled in for table parameters.
    """
    columns = (
        [_to_parameter_column_view(parameter=column) for column in parameter.columns]
        if isinstance(parameter, TableParameter)
        else None
    )
    return ParameterView(
        name=parameter.name,
        description=parameter.description,
        default=parameter.default,
        required=parameter.required,
        param_type=parameter.param_type,
        columns=columns,
    )


def _to_parameter_column_view(parameter: BaseParameter) -> ParameterColumnView:
    return ParameterColumnView(
        name=parameter.name,
        description=parameter.description,
        default=parameter.default,
        required=parameter.required,
        param_type=parameter.param_type,
    )
