"""Read recordings belonging to a dataset."""

from uuid import UUID

from sqlmodel import Session, col, select

from lightly_studio.models.recording import RecordingTable


def get_all_by_dataset_id(session: Session, dataset_id: UUID) -> list[RecordingTable]:
    """Return all recordings belonging to ``dataset_id``."""
    statement = select(RecordingTable).where(col(RecordingTable.dataset_id) == dataset_id)
    return list(session.exec(statement).all())
