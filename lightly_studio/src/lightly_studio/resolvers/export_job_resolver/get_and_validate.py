"""Retrieve and validate an export job."""

from __future__ import annotations

from uuid import UUID

from fastapi import HTTPException
from sqlmodel import Session

from lightly_studio.api.routes.api.status import (
    HTTP_STATUS_BAD_REQUEST,
    HTTP_STATUS_NOT_FOUND,
)
from lightly_studio.models.export_job import ExportJobTable, ExportType
from lightly_studio.resolvers.export_job_resolver.get import get


def get_and_validate(
    session: Session,
    export_key: UUID,
    collection_id: UUID,
    export_type: ExportType,
) -> ExportJobTable:
    """Retrieve an export job or raise.

    Args:
        session: Database session.
        export_key: The UUID returned by the prepare endpoint.
        collection_id: Expected collection owner of the key.
        export_type: Expected export type discriminator.

    Returns:
        The matching ExportJobTable row.

    Raises:
        HTTPException: 404 if the key is not found; 400 if the
            collection_id or export_type do not match the stored row.
    """
    job = get(session=session, export_key=export_key)
    if job is None:
        raise HTTPException(status_code=HTTP_STATUS_NOT_FOUND, detail="Export key not found.")
    if job.collection_id != collection_id:
        raise HTTPException(
            status_code=HTTP_STATUS_BAD_REQUEST,
            detail="Export key does not belong to this collection.",
        )
    if job.export_type != export_type:
        raise HTTPException(
            status_code=HTTP_STATUS_BAD_REQUEST,
            detail="Export key is not valid for this export type.",
        )
    return job
