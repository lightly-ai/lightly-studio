"""Persist a new export job."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlmodel import Session

from lightly_studio.models.export_job import ExportJobTable, ExportType


def create(
    session: Session,
    collection_id: UUID,
    export_type: ExportType,
    filter_json: dict[str, Any],
) -> UUID:
    """Persist a new export job and return its key.

    Args:
        session: Database session.
        collection_id: The collection the export key belongs to.
        export_type: Discriminator for which download endpoint may consume this key.
        filter_json: Serialized filter body (result of ``model_dump(mode="json")``).

    Returns:
        The export key UUID for the created job.
    """
    job = ExportJobTable(
        collection_id=collection_id,
        export_type=export_type,
        filter_json=filter_json,
    )
    session.add(job)
    session.commit()
    session.refresh(job)
    return job.export_key
