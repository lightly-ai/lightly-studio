"""Create recording functionality."""

from __future__ import annotations

from uuid import UUID

from sqlmodel import Session

from lightly_studio.models.dataset import DatasetTable
from lightly_studio.models.recording import RecordingFormat, RecordingTable


def create(session: Session, dataset_id: UUID, uri: str, format_: RecordingFormat) -> UUID:
    """Create a new recording for a dataset.

    Args:
        session: The database session.
        dataset_id: The dataset the recording belongs to.
        uri: Path or object-storage URI of the bag file.
        format_: Format of the recording.

    Returns:
        The UUID of the newly created recording.

    Raises:
        ValueError: If the dataset does not exist, or ``uri`` is empty or whitespace.
    """
    if session.get(DatasetTable, dataset_id) is None:
        raise ValueError(f"Dataset with id {dataset_id} not found.")

    uri = uri.strip()
    if not uri:
        raise ValueError("uri must not be empty.")

    recording = RecordingTable(dataset_id=dataset_id, uri=uri, format=format_)
    session.add(recording)
    session.commit()
    session.refresh(recording)
    return recording.recording_id
