"""API routes for operators."""

from __future__ import annotations

from typing import Any, List
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, HTTPException
from pydantic import BaseModel

from lightly_studio.api.routes.api.status import HTTP_STATUS_NOT_FOUND
from lightly_studio.db_manager import SessionDep
from lightly_studio.plugins.base_operator import BatchSampleOperator, OperatorResult
from lightly_studio.plugins.operator_registry import RegisteredOperatorMetadata, operator_registry
from lightly_studio.plugins.parameter import BaseParameter
from lightly_studio.models.plugin_job import (
    PluginJobCreate,
    PluginJobTable,
    PluginJobView,
)
from lightly_studio.resolvers import plugin_job_resolver
from lightly_studio.services.plugin_job_manager import job_manager

operator_router = APIRouter(prefix="/operators", tags=["operators"])


class ExecuteOperatorRequest(BaseModel):
    """Request model for executing an operator."""

    parameters: dict[str, Any]


class StartJobRequest(BaseModel):
    """Request body for starting a batch operator job."""

    parameters: dict[str, Any]


# --- Operator discovery ---


@operator_router.get("")
def get_operators() -> list[RegisteredOperatorMetadata]:
    """Get all registered operators (id, name, description, type)."""
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


# --- Simple operator execution ---


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
        request: The execution request containing parameters.
        session: Database session.

    Returns:
        The execution result.
    """
    operator = operator_registry.get_by_id(operator_id=operator_id)
    if operator is None:
        raise HTTPException(
            status_code=HTTP_STATUS_NOT_FOUND,
            detail=f"Operator '{operator_id}' not found",
        )

    return operator.execute(
        session=session,
        collection_id=collection_id,
        parameters=request.parameters,
    )


# --- Batch job endpoints (for BatchSampleOperator) ---


@operator_router.post(
    "/collections/{collection_id}/{operator_id}/jobs",
    response_model=PluginJobView,
    status_code=201,
)
def start_operator_job(
    operator_id: str,
    collection_id: UUID,
    request: StartJobRequest,
    session: SessionDep,
    background_tasks: BackgroundTasks,
) -> PluginJobTable:
    """Start a batch job for a BatchSampleOperator.

    Args:
        operator_id: The ID of the operator to execute.
        collection_id: ID of the collection to operate on.
        request: Job request with parameters.
        session: Database session.
        background_tasks: FastAPI background tasks.

    Returns:
        Created job table entry.
    """
    operator = operator_registry.get_by_id(operator_id=operator_id)
    if operator is None:
        raise HTTPException(
            status_code=HTTP_STATUS_NOT_FOUND,
            detail=f"Operator '{operator_id}' not found",
        )

    if not isinstance(operator, BatchSampleOperator):
        raise HTTPException(
            status_code=400,
            detail=f"Operator '{operator_id}' does not support batch job execution",
        )

    # Create job record
    job = plugin_job_resolver.create(
        session=session,
        job_create=PluginJobCreate(
            collection_id=collection_id,
            provider_id=operator_id,
            parameters=request.parameters,
            status="pending",
        ),
    )

    # For prototype: Execute synchronously
    job_manager.execute_job_sync(
        session=session,
        job_id=job.job_id,
        operator=operator,
        collection_id=collection_id,
        parameters=request.parameters,
    )

    # Refresh job to get updated status
    session.refresh(job)
    return job


@operator_router.get("/jobs/{job_id}", response_model=PluginJobView)
def get_job_status(job_id: UUID, session: SessionDep) -> PluginJobTable:
    """Get status of a plugin job.

    Args:
        job_id: ID of the job.
        session: Database session.

    Returns:
        Job table entry.
    """
    job = plugin_job_resolver.get_by_id(session, job_id)
    if not job:
        raise HTTPException(status_code=HTTP_STATUS_NOT_FOUND, detail="Job not found")
    return job


@operator_router.get(
    "/collections/{collection_id}/jobs",
    response_model=List[PluginJobView],
)
def list_jobs(
    collection_id: UUID,
    session: SessionDep,
    limit: int = 50,
    offset: int = 0,
) -> List[PluginJobTable]:
    """List plugin jobs for a collection.

    Args:
        collection_id: ID of the collection.
        session: Database session.
        limit: Maximum number of jobs to return.
        offset: Number of jobs to skip.

    Returns:
        List of job table entries.
    """
    return plugin_job_resolver.get_by_collection_id(
        session=session,
        collection_id=collection_id,
        limit=limit,
        offset=offset,
    )
