"""Read a recording by ID."""

from __future__ import annotations

from uuid import UUID

from sqlmodel import Session

from lightly_studio.models.recording import RecordingTable


def get_by_id(session: Session, recording_id: UUID) -> RecordingTable | None:
    """Return a recording, or ``None`` when it does not exist."""
    return session.get(RecordingTable, recording_id)
