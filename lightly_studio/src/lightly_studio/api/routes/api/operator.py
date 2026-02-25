"""API routes for operators."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from lightly_studio.api.routes.api.status import HTTP_STATUS_NOT_FOUND
from lightly_studio.db_manager import SessionDep
from lightly_studio.models.collection import SampleType
from lightly_studio.plugins import operator_context
from lightly_studio.plugins.base_operator import OperatorResult
from lightly_studio.plugins.operator_context import ExecutionContext
from lightly_studio.plugins.operator_registry import RegisteredOperatorMetadata, operator_registry
from lightly_studio.plugins.parameter import BaseParameter
from lightly_studio.resolvers import collection_resolver
from lightly_studio.resolvers.image_filter import ImageFilter
from lightly_studio.resolvers.sample_resolver.sample_filter import SampleFilter
from lightly_studio.resolvers.video_frame_resolver.video_frame_filter import VideoFrameFilter
from lightly_studio.resolvers.video_resolver.video_filter import VideoFilter

operator_router = APIRouter(prefix="/operators", tags=["operators"])

HTTP_STATUS_UNPROCESSABLE = 422


class OperatorContextRequest(BaseModel):
    """Client-supplied execution context for scoped operator calls.

    If ``sample_id`` is provided, the API translates it to a sample-id filter
    before invoking the operator.
    """

    collection_id: UUID | None = None
    sample_id: UUID | None = None
    filter: ImageFilter | VideoFilter | VideoFrameFilter | None = None


class ExecuteOperatorRequest(BaseModel):
    """Request model for executing an operator."""

    parameters: dict[str, Any]
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
        # Execute the operator
        return operator.execute(
            session=session,
            context=ExecutionContext(collection_id=collection_id),
            parameters=request.parameters,
        )

    # The context may specify a focused sub-collection; fall back to the route collection.
    collection_id = context.collection_id or collection_id
    collection = collection_resolver.get_by_id(session=session, collection_id=collection_id)
    if collection is None:
        raise HTTPException(
            status_code=HTTP_STATUS_NOT_FOUND,
            detail=f"Collection '{collection_id}' not found",
        )

    # Get the scopes for the collection and validate against the scopes supported by the operator.
    collection_scopes = operator_context.get_allowed_scopes_for_collection(
        sample_type=collection.sample_type,
        is_root_collection=collection.parent_collection_id is None,
    )
    if not any(scope in operator.supported_scopes for scope in collection_scopes):
        raise HTTPException(
            status_code=HTTP_STATUS_UNPROCESSABLE,
            detail=(
                f"Operator '{operator_id}' does not support scope(s) "
                f"{[scope.value for scope in collection_scopes]}. "
                f"Supported scopes: {[s.value for s in operator.supported_scopes]}"
            ),
        )

    # Construct the filter: if sample_id is provided it is preferred against the provided filter.
    effective_filter = _build_filter_from_context(
        context=context, sample_type=collection.sample_type)

    # Execute the operator
    return operator.execute(
        session=session,
        context=ExecutionContext(collection_id=collection_id, filter=effective_filter),
        parameters=request.parameters,
    )


def _build_filter_from_context(
    context: OperatorContextRequest,
    sample_type: SampleType,
) -> ImageFilter | VideoFilter | VideoFrameFilter | None:
    """Build the typed filter to pass to the operator.

    If ``context.sample_id`` is set, wraps it in a ``SampleFilter`` and returns the
    appropriate typed filter for the collection (``VideoFilter``, ``VideoFrameFilter``,
    or ``ImageFilter``). If no ``sample_id`` is provided, passes ``context.filter``
    through unchanged.
    """
    if context.sample_id is None:
        return context.filter

    sample_filter = SampleFilter(sample_ids=[context.sample_id])
    if sample_type == SampleType.VIDEO:
        return VideoFilter(sample_filter=sample_filter)
    if sample_type == SampleType.VIDEO_FRAME:
        return VideoFrameFilter(sample_filter=sample_filter)
    if sample_type == SampleType.IMAGE:
        return ImageFilter(sample_filter=sample_filter)
    return None
