"""Persist a new export job."""

from __future__ import annotations

from uuid import UUID

from sqlmodel import Session

from lightly_studio.models.export_job import ExportJobTable


def create(
    session: Session,
    collection_id: UUID,
    export_path: str,
) -> ExportJobTable:
    """Persist a new export job and return it.

    Args:
        session: Database session.
        collection_id: Collection the export was prepared for.
        export_path: Absolute path to the pre-generated export file or directory.

    Returns:
        The created ExportJobTable row.
    """
    job = ExportJobTable(collection_id=collection_id, export_path=export_path)
    session.add(job)
    session.commit()
    session.refresh(job)
    return job
