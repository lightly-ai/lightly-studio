"""API routes for auto-labeling functionality."""

from __future__ import annotations

from typing import Any, List
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, HTTPException
from pydantic import BaseModel

from lightly_studio.auto_labeling.base_provider import ProviderParameter
from lightly_studio.auto_labeling.provider_registry import provider_registry
from lightly_studio.db_manager import SessionDep
from lightly_studio.models.auto_labeling_job import (
    AutoLabelingJobCreate,
    AutoLabelingJobTable,
    AutoLabelingJobView,
)
from lightly_studio.resolvers import auto_labeling_job_resolver
from lightly_studio.services.auto_labeling_job_manager import job_manager

auto_labeling_router = APIRouter()


@auto_labeling_router.get("/providers")
def get_providers() -> List[dict]:
    """Get all available auto-labeling providers.

    Returns:
        List of provider metadata dictionaries.
    """
    return provider_registry.get_all_metadata()


@auto_labeling_router.get("/providers/{provider_id}/parameters")
def get_provider_parameters(provider_id: str) -> List[ProviderParameter]:
    """Get parameters for a specific provider.

    Args:
        provider_id: ID of the provider.

    Returns:
        List of provider parameters.

    Raises:
        HTTPException: If provider is not found.
    """
    provider = provider_registry.get_by_id(provider_id)
    if not provider:
        raise HTTPException(
            status_code=404, detail=f"Provider {provider_id} not found"
        )
    return provider.parameters


class StartJobRequest(BaseModel):
    """Request body for starting an auto-labeling job."""

    provider_id: str
    parameters: dict[str, Any]


@auto_labeling_router.post(
    "/collections/{collection_id}/jobs",
    response_model=AutoLabelingJobView,
    status_code=201,
)
def start_auto_labeling_job(
    collection_id: UUID,
    request: StartJobRequest,
    session: SessionDep,
    background_tasks: BackgroundTasks,
) -> AutoLabelingJobTable:
    """Start a new auto-labeling job.

    Args:
        collection_id: ID of the collection to operate on.
        request: Job request with provider ID and parameters.
        session: Database session.
        background_tasks: FastAPI background tasks.

    Returns:
        Created job table entry.

    Raises:
        HTTPException: If provider is not found.
    """
    # Validate provider exists
    provider = provider_registry.get_by_id(request.provider_id)
    if not provider:
        raise HTTPException(
            status_code=404, detail=f"Provider {request.provider_id} not found"
        )

    # Create job record
    job = auto_labeling_job_resolver.create(
        session=session,
        job_create=AutoLabelingJobCreate(
            collection_id=collection_id,
            provider_id=request.provider_id,
            parameters=request.parameters,
            status="pending",
        ),
    )

    # For prototype: Execute synchronously instead of async
    # This blocks the API call but is simpler and works without async support
    job_manager.execute_job_sync(
        session=session,
        job_id=job.job_id,
        provider=provider,
        collection_id=collection_id,
        parameters=request.parameters,
    )

    # Refresh job to get updated status
    session.refresh(job)
    return job


@auto_labeling_router.get("/jobs/{job_id}", response_model=AutoLabelingJobView)
def get_job_status(job_id: UUID, session: SessionDep) -> AutoLabelingJobTable:
    """Get status of an auto-labeling job.

    Args:
        job_id: ID of the job.
        session: Database session.

    Returns:
        Job table entry.

    Raises:
        HTTPException: If job is not found.
    """
    job = auto_labeling_job_resolver.get_by_id(session, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


@auto_labeling_router.get(
    "/collections/{collection_id}/jobs",
    response_model=List[AutoLabelingJobView],
)
def list_jobs(
    collection_id: UUID,
    session: SessionDep,
    limit: int = 50,
    offset: int = 0,
) -> List[AutoLabelingJobTable]:
    """List auto-labeling jobs for a collection.

    Args:
        collection_id: ID of the collection.
        session: Database session.
        limit: Maximum number of jobs to return.
        offset: Number of jobs to skip.

    Returns:
        List of job table entries.
    """
    return auto_labeling_job_resolver.get_by_collection_id(
        session=session,
        collection_id=collection_id,
        limit=limit,
        offset=offset,
    )
