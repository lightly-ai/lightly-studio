"""Handler for database operations related to annotations."""

from __future__ import annotations

from uuid import UUID

from sqlmodel import Session, col, delete

from lightly_studio.models.annotation.annotation_base import (
    AnnotationBaseTable,
)
from lightly_studio.resolvers import annotation_resolver
from lightly_studio.resolvers.annotations.annotations_filter import (
    AnnotationsFilter,
)


def delete_annotations(
    session: Session,
    annotation_label_ids: list[UUID] | None,
) -> None:
    """Delete all annotations and their tag links using filters.

    Args:
        session: Database session.
        annotation_label_ids: List of annotation label IDs to filter by.
    """
    annotations = annotation_resolver.get_all(
        session,
        filters=AnnotationsFilter(
            annotation_label_ids=annotation_label_ids,
        ),
    ).annotations

    # Delete annotation details first
    for annotation in annotations:
        if annotation.object_detection_details:
            session.delete(annotation.object_detection_details)
        if annotation.segmentation_details:
            session.delete(annotation.segmentation_details)
    session.commit()

    # Now delete the annotations themselves
    annotation_ids = [annotation.sample_id for annotation in annotations]
    if annotation_ids:
        session.exec(  # type: ignore
            delete(AnnotationBaseTable).where(
                col(AnnotationBaseTable.sample_id).in_(annotation_ids)
            )
        )
        session.commit()
