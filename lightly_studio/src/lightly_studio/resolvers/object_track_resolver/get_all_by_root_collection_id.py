"""Get all object tracks for a dataset."""

from __future__ import annotations

from collections.abc import Sequence
from uuid import UUID

from sqlmodel import Session, col, select

from lightly_studio.models.annotation.object_track import ObjectTrackTable


def get_all_by_root_collection_id(
    session: Session,
    root_collection_id: UUID,
) -> Sequence[ObjectTrackTable]:
    """Retrieve all object tracks for a given root collection."""
    stmt = select(ObjectTrackTable).where(
        col(ObjectTrackTable.root_collection_id) == root_collection_id
    )
    return session.exec(stmt).all()
