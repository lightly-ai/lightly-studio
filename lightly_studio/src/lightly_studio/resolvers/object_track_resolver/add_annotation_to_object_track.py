"""Link an existing annotation to a object track."""

from __future__ import annotations

from uuid import UUID

from sqlmodel import Session, col, select

from lightly_studio.models.annotation.annotation_base import (
    AnnotationBaseTable,
    AnnotationType,
)
from lightly_studio.resolvers import annotation_resolver
from lightly_studio.resolvers.annotation_resolver import annotation_helper


def add_annotation_to_object_track(
    session: Session,
    annotation_id: UUID,
    object_track_id: UUID,
) -> AnnotationBaseTable:
    """Link an existing annotation to a object track by setting its object_track_id.

    Args:
        session: Database session for executing the operation.
        annotation_id: UUID of the annotation to link.
        object_track_id: UUID of the object track to link the annotation to.

    Returns:
        The updated annotation with object_track_id set.
    """
    annotation = annotation_resolver.get_by_id(session=session, annotation_id=annotation_id)
    if not annotation:
        raise ValueError(f"Annotation with ID {annotation_id} not found.")
    if annotation.annotation_type == AnnotationType.CUBOID_3D:
        existing = session.exec(
            select(AnnotationBaseTable).where(
                col(AnnotationBaseTable.annotation_type) == AnnotationType.CUBOID_3D,
                col(AnnotationBaseTable.parent_sample_id) == annotation.parent_sample_id,
                col(AnnotationBaseTable.object_track_id) == object_track_id,
                col(AnnotationBaseTable.sample_id) != annotation.sample_id,
            )
        ).first()
        if existing is not None:
            raise ValueError("A cuboid for this object track already exists on this group.")
    return annotation_helper.update_annotation_object(
        session=session,
        annotation=annotation,
        fields_to_update={"object_track_id": object_track_id},
    )
