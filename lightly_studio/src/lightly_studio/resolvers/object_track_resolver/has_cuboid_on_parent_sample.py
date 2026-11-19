"""Check whether an object track has a cuboid on a parent sample."""

from __future__ import annotations

from uuid import UUID

from sqlmodel import Session, col, select

from lightly_studio.models.annotation.annotation_base import (
    AnnotationBaseTable,
    AnnotationType,
)


def has_cuboid_on_parent_sample(
    session: Session,
    object_track_id: UUID,
    parent_sample_id: UUID,
) -> bool:
    """Return whether the object track has a cuboid on the parent sample.

    An object track has at most one cuboid on each parent sample.

    Args:
        session: Database session for executing the operation.
        object_track_id: UUID of the object track.
        parent_sample_id: UUID of the parent sample, for example a point cloud group.

    Returns:
        True if a cuboid of the object track is on the parent sample.
    """
    existing = session.exec(
        select(AnnotationBaseTable.sample_id).where(
            col(AnnotationBaseTable.annotation_type) == AnnotationType.CUBOID_3D,
            col(AnnotationBaseTable.parent_sample_id) == parent_sample_id,
            col(AnnotationBaseTable.object_track_id) == object_track_id,
        )
    ).first()
    return existing is not None
