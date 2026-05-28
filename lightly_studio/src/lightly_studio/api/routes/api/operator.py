"""API routes for operators."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Optional
from uuid import UUID

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from lightly_studio.api.routes.api.status import (
    HTTP_STATUS_CONFLICT,
    HTTP_STATUS_NOT_FOUND,
)
from lightly_studio.db_manager import SessionDep
from lightly_studio.plugins import operator_context
from lightly_studio.plugins.base_operator import OperatorResult, OperatorStatus
from lightly_studio.plugins.execution_registry import (
    ExecutionRecord,
    execution_registry,
    worker_session,
)
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
    context: OperatorContextRequest


class OperatorExecutionResponse(BaseModel):
    """Per-execution state surfaced to the GUI."""

    execution_id: UUID
    operator_id: str
    operator_name: str
    status: OperatorStatus
    started_at: datetime
    finished_at: Optional[datetime] = None
    result: Optional[OperatorResult] = None
    error_message: Optional[str] = None

    @classmethod
    def from_record(cls, record: ExecutionRecord) -> "OperatorExecutionResponse":
        return cls(
            execution_id=record.execution_id,
            operator_id=record.operator_id,
            operator_name=record.operator_name,
            status=record.status,
            started_at=record.started_at,
            finished_at=record.finished_at,
            result=record.result,
            error_message=record.error_message,
        )


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


@operator_router.post("/{operator_id}/execute", response_model=OperatorExecutionResponse)
def execute_operator(
    operator_id: str,
    request: ExecuteOperatorRequest,
    session: SessionDep,
) -> OperatorExecutionResponse:
    """Dispatch an operator to the background worker pool.

    Returns immediately with an ``OperatorExecutionResponse`` whose status is
    ``RUNNING``. Poll ``GET /operators/executions/{execution_id}`` (or list all
    via ``GET /operators/executions``) to follow progress.
    """
    operator = operator_registry.get_by_id(operator_id=operator_id)
    if operator is None:
        raise HTTPException(
            status_code=HTTP_STATUS_NOT_FOUND,
            detail=f"Operator '{operator_id}' not found",
        )

    if operator.status != OperatorStatus.READY:
        if operator.status in (OperatorStatus.PENDING, OperatorStatus.STARTING):
            message = f"Operator '{operator_id}' is still starting, please try again in a moment."
        elif operator.status in (OperatorStatus.STOPPING, OperatorStatus.STOPPED):
            message = f"Operator '{operator_id}' has been stopped and cannot be executed."
        else:
            message = f"Operator '{operator_id}' is in an error state and cannot be executed."
        raise HTTPException(status_code=HTTP_STATUS_CONFLICT, detail=message)

    context = request.context

    collection = collection_resolver.get_by_id(session=session, collection_id=context.collection_id)
    if collection is None:
        raise HTTPException(
            status_code=HTTP_STATUS_NOT_FOUND,
            detail=f"Collection '{context.collection_id}' not found",
        )

    collection_scopes = operator_context.get_allowed_scopes_for_collection(
        sample_type=collection.sample_type,
        is_root_collection=collection.parent_collection_id is None,
    )
    if not any(scope in operator.supported_scopes for scope in collection_scopes):
        supported = ", ".join(s.value for s in operator.supported_scopes)
        raise HTTPException(
            status_code=HTTP_STATUS_CONFLICT,
            detail=(
                f"Operator '{operator.name}' cannot be executed in this context. "
                f"Supported scopes: {supported}."
            ),
        )

    record = execution_registry.submit(
        operator=operator,
        operator_id=operator_id,
        session_factory=worker_session,
        context=ExecutionContext(
            collection_id=context.collection_id, context_filter=context.context_filter
        ),
        parameters=request.parameters,
    )
    return OperatorExecutionResponse.from_record(record)


@operator_router.get("/executions", response_model=list[OperatorExecutionResponse])
def list_executions() -> list[OperatorExecutionResponse]:
    """List all known executions (running, succeeded, failed)."""
    return [OperatorExecutionResponse.from_record(r) for r in execution_registry.list_all()]


@operator_router.get(
    "/executions/{execution_id}", response_model=OperatorExecutionResponse
)
def get_execution(execution_id: UUID) -> OperatorExecutionResponse:
    """Get the current state of a single execution."""
    record = execution_registry.get(execution_id)
    if record is None:
        raise HTTPException(
            status_code=HTTP_STATUS_NOT_FOUND,
            detail=f"Execution '{execution_id}' not found",
        )
    return OperatorExecutionResponse.from_record(record)


@operator_router.delete("/executions/{execution_id}", status_code=204)
def dismiss_execution(execution_id: UUID) -> None:
    """Remove a finished execution from the registry. Refuses if still running."""
    record = execution_registry.get(execution_id)
    if record is None:
        raise HTTPException(
            status_code=HTTP_STATUS_NOT_FOUND,
            detail=f"Execution '{execution_id}' not found",
        )
    if record.status == OperatorStatus.RUNNING:
        raise HTTPException(
            status_code=HTTP_STATUS_CONFLICT,
            detail="Execution is still running and cannot be dismissed.",
        )
    execution_registry.remove(execution_id)
