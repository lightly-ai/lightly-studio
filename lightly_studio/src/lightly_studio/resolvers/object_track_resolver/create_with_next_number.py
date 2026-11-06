"""Create an object track with the next free number in a dataset."""

from __future__ import annotations

import threading
from uuid import UUID

from sqlalchemy import func
from sqlmodel import Session, col, select

from lightly_studio.models.annotation.object_track import ObjectTrackTable

# Requests run in a thread pool, so numbers are allocated one at a time. A lock cannot
# serialize several server processes sharing one PostgreSQL database.
_NUMBER_ALLOCATION_LOCK = threading.Lock()


def create_with_next_number(session: Session, dataset_id: UUID) -> ObjectTrackTable:
    """Create and commit a track numbered one above the dataset's highest number.

    Args:
        session: The database session.
        dataset_id: The dataset the track belongs to.

    Returns:
        The new track. The first track of a dataset has number 1.
    """
    with _NUMBER_ALLOCATION_LOCK:
        highest = session.exec(
            select(func.max(ObjectTrackTable.object_track_number)).where(
                col(ObjectTrackTable.dataset_id) == dataset_id
            )
        ).one()
        track = ObjectTrackTable(
            object_track_number=1 if highest is None else highest + 1, dataset_id=dataset_id
        )
        session.add(track)
        session.commit()
        session.refresh(track)
    return track
