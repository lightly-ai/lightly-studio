"""Compute the next available object track number for a dataset."""

from __future__ import annotations

from uuid import UUID

from sqlmodel import Session, col, func, select

from lightly_studio.models.annotation.object_track import ObjectTrackTable


def next_track_number(session: Session, dataset_id: UUID) -> int:
    """Return the next dataset-unique object_track_number."""
    maximum = session.exec(
        select(func.max(ObjectTrackTable.object_track_number)).where(
            col(ObjectTrackTable.dataset_id) == dataset_id
        )
    ).one()
    return 1 if maximum is None else maximum + 1
