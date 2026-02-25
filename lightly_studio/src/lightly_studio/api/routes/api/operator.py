"""API routes for operators."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from lightly_studio.api.routes.api.status import HTTP_STATUS_NOT_FOUND
from lightly_studio.db_manager import SessionDep
from lightly_studio.models.collection import SampleType
from lightly_studio.plugins.base_operator import OperatorResult, OperatorStatus
from lightly_studio.plugins.execution_context import ExecutionContext
from lightly_studio.plugins.operator_registry import RegisteredOperatorMetadata, operator_registry
from lightly_studio.plugins.operator_scope import (
    OperatorScope,
    get_allowed_scopes_for_collection,
    get_scope_for_sample_type,
)
from lightly_studio.plugins.parameter import BaseParameter
from lightly_studio.resolvers import collection_resolver
from lightly_studio.resolvers.image_filter import ImageFilter
from lightly_studio.resolvers.sample_resolver.sample_filter import SampleFilter
from lightly_studio.resolvers.video_resolver.video_filter import VideoFilter

operator_router = APIRouter(prefix="/operators", tags=["operators"])

HTTP_STATUS_CONFLICT = 409
HTTP_STATUS_UNPROCESSABLE = 422


class OperatorContextRequest(BaseModel):
    """Client-supplied execution context for scoped operator calls.

    If ``sample_id`` is provided, the API translates it to a sample-id filter
    before invoking the operator.
    """

    collection_id: UUID | None = None
    sample_id: UUID | None = None
    filter: ImageFilter | VideoFilter | None = None


class ExecuteOperatorRequest(BaseModel):
    """Request model for executing an operator."""

    parameters: dict[str, Any]
    context: OperatorContextRequest | None = None


@operator_router.get("")
def get_operators() -> list[RegisteredOperatorMetadata]:
    """Get all registered operators (id, name, status, scopes)."""
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

    if operator.status != OperatorStatus.READY:
        raise HTTPException(
            status_code=HTTP_STATUS_CONFLICT,
            detail=f"Operator '{operator_id}' is not ready (status: {operator.status.value})",
        )

    req_ctx = request.context

    # Resolve the target collection: the context may specify a focused sub-collection
    # (e.g. a frame or video collection within a group); fall back to the route collection.
    target_collection_id = (
        req_ctx.collection_id if req_ctx and req_ctx.collection_id else collection_id
    )
    target_collection = collection_resolver.get_by_id(session=session, collection_id=target_collection_id)
    if target_collection is None:
        raise HTTPException(
            status_code=HTTP_STATUS_NOT_FOUND,
            detail=f"Collection '{target_collection_id}' not found",
        )

    collection_type = target_collection.sample_type
    allowed_scopes = get_allowed_scopes_for_collection(
        sample_type=collection_type,
        is_root_collection=target_collection.parent_collection_id is None,
    )
    effective_filter = _build_filter_from_context(
        filter_obj=req_ctx.filter if req_ctx else None,
        sample_id=req_ctx.sample_id if req_ctx else None,
        collection_type=collection_type,
    )

    # Validate that the operator supports at least one valid scope for this collection context.
    if not any(scope in operator.supported_scopes for scope in allowed_scopes):
        raise HTTPException(
            status_code=HTTP_STATUS_UNPROCESSABLE,
            detail=(
                f"Operator '{operator_id}' does not support scope(s) "
                f"{[scope.value for scope in allowed_scopes]}. "
                f"Supported scopes: {[s.value for s in operator.supported_scopes]}"
            ),
        )

    context = ExecutionContext(
        collection_id=target_collection_id,
        filter=effective_filter,
    )

    return operator.execute(
        session=session,
        context=context,
        parameters=request.parameters,
    )


def _build_filter_from_context(
    *,
    filter_obj: ImageFilter | VideoFilter | None,
    sample_id: UUID | None,
    collection_type: SampleType,
) -> ImageFilter | VideoFilter | None:
    """Translate ``sample_id`` to a dedicated filter payload."""
    if sample_id is None:
        return filter_obj

    sample_filter = SampleFilter(sample_ids=[sample_id])

    if get_scope_for_sample_type(sample_type=collection_type) == OperatorScope.VIDEO:
        return VideoFilter(sample_filter=sample_filter)
    return ImageFilter(sample_filter=sample_filter)
