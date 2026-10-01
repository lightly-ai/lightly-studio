"""Query an export job by key."""

from __future__ import annotations

from uuid import UUID

from sqlmodel import Session

from lightly_studio.models.export_job import ExportJobTable


def get(session: Session, export_key: UUID) -> ExportJobTable | None:
    """Return the ExportJobTable row for *export_key*, or None if not found.

    Args:
        session: Database session.
        export_key: The UUID returned by the prepare endpoint.

    Returns:
        The ExportJobTable row, or None if no matching row exists.
    """
    return session.get(ExportJobTable, export_key)
