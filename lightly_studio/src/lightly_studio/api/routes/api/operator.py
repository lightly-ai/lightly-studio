"""API routes for operators."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from lightly_studio.api.routes.api.status import (
    HTTP_STATUS_NOT_FOUND,
    HTTP_STATUS_UNPROCESSABLE_ENTITY,
)
from lightly_studio.db_manager import SessionDep
from lightly_studio.plugins import operator_context
from lightly_studio.plugins.base_operator import OperatorResult
from lightly_studio.plugins.operator_context import AnyFilter, ExecutionContext
from lightly_studio.plugins.operator_registry import RegisteredOperatorMetadata, operator_registry
from lightly_studio.plugins.parameter import BaseParameter
from lightly_studio.resolvers import collection_resolver

operator_router = APIRouter(prefix="/operators", tags=["operators"])


class OperatorContextRequest(BaseModel):
    """Client-supplied execution context for scoped operator calls."""

    collection_id: UUID
    """The collection_id the operator shall be executed on."""

    context_filter: AnyFilter = None
    """The filter for the provided collection."""


class ExecuteOperatorRequest(BaseModel):
    """Request model for executing an operator."""

    parameters: dict[str, Any]
    # TODO (Jonas, 3/2026): The context will become non optional,
    # when removing the collection_id form the route.
    context: OperatorContextRequest | None = None


@operator_router.get("")
def get_operators() -> list[RegisteredOperatorMetadata]:
    """Get all registered operators (id, name)."""
    return operator_registry.get_all_metadata()


@operator_router.get("/{operator_id}/parameters")
def get_operator_parameters(operator_id: str) -> list[BaseParameter]:
    """Get the parameters for a registered operator."""
    operator = operator_registry.get_by_id(operator_id=operator_id)
    if operator is None:
        raise HTTPException(
            status_code=HTTP_STATUS_NOT_FOUND,
            detail=f"Operator '{operator_id}' not found",
        )
    return operator.parameters


@operator_router.post(
    "/collections/{collection_id}/{operator_id}/execute", response_model=OperatorResult
)
def execute_operator(
    operator_id: str,
    # TODO (Jonas, 3/2026): The collection_id will be moved to the request body.
    collection_id: UUID,
    request: ExecuteOperatorRequest,
    session: SessionDep,
) -> OperatorResult:
    """Execute an operator with the provided parameters.

    Args:
        operator_id: The ID of the operator to execute.
        collection_id: The ID of the collection to operate on.
        request: The execution request containing parameters and optional context.
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

    context = request.context
    if context is None:
        context = OperatorContextRequest(collection_id=collection_id, context_filter=None)

    # The context may specify a focused sub-collection; fall back to the route collection.
    collection = collection_resolver.get_by_id(session=session, collection_id=context.collection_id)
    if collection is None:
        raise HTTPException(
            status_code=HTTP_STATUS_NOT_FOUND,
            detail=f"Collection '{context.collection_id}' not found",
        )

    # Get the scopes for the collection and validate against the scopes supported by the operator.
    collection_scopes = operator_context.get_allowed_scopes_for_collection(
        sample_type=collection.sample_type,
        is_root_collection=collection.parent_collection_id is None,
    )
    if not any(scope in operator.supported_scopes for scope in collection_scopes):
        raise HTTPException(
            status_code=HTTP_STATUS_UNPROCESSABLE_ENTITY,
            detail=(
                f"Operator '{operator_id}' does not support scope(s) "
                f"{[scope.value for scope in collection_scopes]}. "
                f"Supported scopes: {[s.value for s in operator.supported_scopes]}"
            ),
        )

    # Execute the operator
    return operator.execute(
        session=session,
        context=ExecutionContext(
            collection_id=context.collection_id, context_filter=context.context_filter
        ),
        parameters=request.parameters,
    )
