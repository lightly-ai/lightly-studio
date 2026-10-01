"""Delete an export job."""

from __future__ import annotations

from uuid import UUID

from sqlmodel import Session

from lightly_studio.resolvers import export_job_resolver


def delete(session: Session, export_key: UUID) -> bool:
    """Delete an export job from the database.

    Args:
        session: Database session.
        export_key: The UUID of the export job to delete.

    Returns:
        True if the job was deleted, False if not found.
    """
    job = export_job_resolver.get(session=session, export_key=export_key)
    if job is None:
        return False
    session.delete(job)
    session.commit()
    return True
