"""Set the reference frames of a recording."""

from __future__ import annotations

from collections.abc import Sequence
from uuid import UUID

from sqlmodel import Session

from lightly_studio.models.recording import RecordingTable


def set_reference_frame_ids(session: Session, recording_id: UUID, frame_ids: Sequence[str]) -> None:
    """Store the frames the scene of a recording can be shown in.

    Args:
        session: The database session.
        recording_id: The ID of the recording.
        frame_ids: The coordinate frame ids, in menu order. The first is the default.

    Raises:
        ValueError: If the recording does not exist.
    """
    recording = session.get(RecordingTable, recording_id)
    if recording is None:
        raise ValueError(f"Recording with id {recording_id} not found.")
    recording.reference_frame_ids = list(frame_ids)
    session.add(recording)
    session.commit()
