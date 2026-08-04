"""Persist a new export job."""

from __future__ import annotations

from sqlmodel import Session

from lightly_studio.models.export_job import ExportJobTable


def create(
    session: Session,
    export_path: str,
) -> ExportJobTable:
    """Persist a new export job and return it.

    Args:
        session: Database session.
        export_path: Absolute path to the pre-generated export file or directory.

    Returns:
        The created ExportJobTable row.
    """
    job = ExportJobTable(export_path=export_path)
    session.add(job)
    session.commit()
    session.refresh(job)
    return job
