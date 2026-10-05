"""API routes for operators."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from lightly_studio.api.routes.api.status import HTTP_STATUS_NOT_FOUND
from lightly_studio.database.db_manager import SessionDep
from lightly_studio.plugins.base_operator import OperatorResult
from lightly_studio.plugins.operator_context import AnyFilter, ExecutionContext
from lightly_studio.plugins.operator_registry import RegisteredOperatorMetadata, operator_registry
from lightly_studio.resolvers import collection_resolver
from lightly_studio.services import operator_service
from lightly_studio.services.operator_service import ParameterView

operator_router = APIRouter(prefix="/operators", tags=["operators"])


class OperatorContextRequest(BaseModel):
    """Client-supplied execution context for scoped operator calls."""

    collection_id: UUID
    """The collection_id the operator shall be executed on."""

    context_filter: AnyFilter | None = None
    """The filter for the provided collection."""


class ExecuteOperatorRequest(BaseModel):
    """Request model for executing an operator."""

    parameters: dict[str, Any]
    context: OperatorContextRequest


@operator_router.get("")
def get_operators() -> list[RegisteredOperatorMetadata]:
    """Get all registered operators (id, name)."""
    return operator_registry.get_all_metadata()


@operator_router.get("/{operator_id}/parameters")
def get_operator_parameters(operator_id: str) -> list[ParameterView]:
    """Get the parameters for a registered operator."""
    operator = operator_registry.get_by_id(operator_id=operator_id)
    if operator is None:
        raise HTTPException(
            status_code=HTTP_STATUS_NOT_FOUND,
            detail=f"Operator '{operator_id}' not found",
        )
    return [
        operator_service.to_parameter_view(parameter=parameter) for parameter in operator.parameters
    ]


@operator_router.post("/{operator_id}/execute", response_model=OperatorResult)
def execute_operator(
    operator_id: str,
    request: ExecuteOperatorRequest,
    session: SessionDep,
) -> OperatorResult:
    """Execute an operator with the provided parameters.

    Args:
        operator_id: The ID of the operator to execute.
        request: The execution request containing parameters and context.
        session: Database session.

    Returns:
        The execution result.
    """
    # Get the operator
    operator = operator_registry.get_by_id(operator_id=operator_id)
    if operator is None:
        raise HTTPException(
            status_code=HTTP_STATUS_NOT_FOUND,
            detail=f"Operator '{operator_id}' not found",
        )

    status_error = operator_service.get_status_error(operator=operator, operator_ref=operator_id)
    if status_error is not None:
        return OperatorResult(success=False, message=status_error)

    context = request.context

    # The context may specify a focused sub-collection; fall back to the route collection.
    collection = collection_resolver.get_by_id(session=session, collection_id=context.collection_id)
    if collection is None:
        raise HTTPException(
            status_code=HTTP_STATUS_NOT_FOUND,
            detail=f"Collection '{context.collection_id}' not found",
        )

    scope_error = operator_service.get_scope_error(operator=operator, collection=collection)
    if scope_error is not None:
        return OperatorResult(success=False, message=scope_error)

    # Execute the operator
    return operator.execute(
        session=session,
        context=ExecutionContext(
            collection_id=context.collection_id, context_filter=context.context_filter
        ),
        parameters=request.parameters,
    )
