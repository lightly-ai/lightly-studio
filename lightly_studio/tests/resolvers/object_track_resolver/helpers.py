"""Helper functions for object track resolver tests."""

from __future__ import annotations

from uuid import UUID

from sqlmodel import Session

from lightly_studio.models.annotation.object_track import ObjectTrackTable
from lightly_studio.resolvers import object_track_resolver


def create_track(
    session: Session,
    dataset_id: UUID,
    object_track_number: int = 1,
) -> ObjectTrackTable:
    """Helper to create an object track for testing."""
    return object_track_resolver.create_track(
        session=session,
        object_track_number=object_track_number,
        dataset_id=dataset_id,
    )
