"""Get the cuboid annotations of several object tracks."""

from __future__ import annotations

from collections.abc import Collection
from uuid import UUID

from sqlalchemy.orm import selectinload
from sqlmodel import Session, col, select

from lightly_studio.models.annotation.annotation_base import (
    AnnotationBaseTable,
    AnnotationType,
)


def get_cuboids_by_object_track_ids(
    session: Session, object_track_ids: Collection[UUID]
) -> list[AnnotationBaseTable]:
    """Return the cuboid annotations of the tracks, with their geometry preloaded."""
    if not object_track_ids:
        return []
    query = (
        select(AnnotationBaseTable)
        .where(
            col(AnnotationBaseTable.object_track_id).in_(object_track_ids),
            col(AnnotationBaseTable.annotation_type) == AnnotationType.CUBOID_3D,
        )
        .options(
            selectinload(AnnotationBaseTable.cuboid_3d_details),
            selectinload(AnnotationBaseTable.sample),
        )
    )
    return list(session.exec(query).all())
