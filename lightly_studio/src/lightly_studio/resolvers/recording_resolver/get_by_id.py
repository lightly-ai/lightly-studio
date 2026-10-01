"""Get a recording by its ID."""

from __future__ import annotations

from uuid import UUID

from sqlmodel import Session

from lightly_studio.models.recording import RecordingTable


def get_by_id(session: Session, recording_id: UUID) -> RecordingTable | None:
    """Retrieve a single recording by its recording_id.

    Args:
        session: Database session for executing the operation.
        recording_id: UUID of the recording to retrieve.

    Returns:
        The RecordingTable instance, or None if not found.
    """
    return session.get(RecordingTable, recording_id)
