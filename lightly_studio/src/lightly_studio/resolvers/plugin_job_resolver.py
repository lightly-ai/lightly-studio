"""Handler for database operations related to plugin jobs."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlmodel import Session, select

from lightly_studio.models.plugin_job import (
    PluginJobCreate,
    PluginJobStatus,
    PluginJobTable,
)


def create(
    session: Session, job_create: PluginJobCreate
) -> PluginJobTable:
    """Create a new plugin job in the database.

    Args:
        session: Database session.
        job_create: Job creation data.

    Returns:
        Created job table entry.
    """
    job = PluginJobTable.model_validate(job_create)
    session.add(job)
    session.commit()
    session.refresh(job)
    return job


def get_by_id(session: Session, job_id: UUID) -> PluginJobTable | None:
    """Retrieve a single job by ID.

    Args:
        session: Database session.
        job_id: Job ID to retrieve.

    Returns:
        Job table entry if found, None otherwise.
    """
    return session.exec(
        select(PluginJobTable).where(PluginJobTable.job_id == job_id)
    ).one_or_none()


def get_by_collection_id(
    session: Session, collection_id: UUID, limit: int = 50, offset: int = 0
) -> list[PluginJobTable]:
    """Retrieve all jobs for a collection with pagination.

    Args:
        session: Database session.
        collection_id: Collection ID to filter by.
        limit: Maximum number of jobs to return.
        offset: Number of jobs to skip.

    Returns:
        List of job table entries.
    """
    query = (
        select(PluginJobTable)
        .where(PluginJobTable.collection_id == collection_id)
        .order_by(PluginJobTable.created_at.desc())
        .offset(offset)
        .limit(limit)
    )
    return list(session.exec(query).all())


def update_status(
    session: Session,
    job_id: UUID,
    status: PluginJobStatus,
    error_message: str | None = None,
    processed_count: int | None = None,
    error_count: int | None = None,
    result_tag_id: UUID | None = None,
    started_at: datetime | None = None,
    completed_at: datetime | None = None,
) -> PluginJobTable | None:
    """Update job status and related fields.

    Args:
        session: Database session.
        job_id: Job ID to update.
        status: New status.
        error_message: Optional error message.
        processed_count: Optional number of processed samples.
        error_count: Optional number of errors.
        result_tag_id: Optional result tag ID.
        started_at: Optional job start time.
        completed_at: Optional job completion time.

    Returns:
        Updated job table entry if found, None otherwise.
    """
    job = get_by_id(session, job_id)
    if not job:
        return None

    job.status = status
    if error_message is not None:
        job.error_message = error_message
    if processed_count is not None:
        job.processed_count = processed_count
    if error_count is not None:
        job.error_count = error_count
    if result_tag_id is not None:
        job.result_tag_id = result_tag_id
    if started_at is not None:
        job.started_at = started_at
    if completed_at is not None:
        job.completed_at = completed_at

    session.add(job)
    session.commit()
    session.refresh(job)
    return job
