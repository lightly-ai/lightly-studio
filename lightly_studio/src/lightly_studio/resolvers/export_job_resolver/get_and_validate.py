"""Retrieve and validate an export job."""

from __future__ import annotations

from uuid import UUID

from sqlmodel import Session

from lightly_studio.models.export_job import ExportJobTable, ExportType
from lightly_studio.resolvers import export_job_resolver


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
        LookupError: If the key is not found.
        ValueError: If the collection_id or export_type do not match the stored row.
    """
    job = export_job_resolver.get(session=session, export_key=export_key)
    if job is None:
        raise LookupError("Export key not found.")
    if job.collection_id != collection_id:
        raise ValueError("Export key does not belong to this collection.")
    if job.export_type != export_type:
        raise ValueError("Export key is not valid for this export type.")
    return job
