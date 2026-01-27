"""Handler for database operations related to annotations."""

from __future__ import annotations

from uuid import UUID

from sqlmodel import Session, col, delete

from lightly_studio.models.annotation.annotation_base import (
    AnnotationBaseTable,
)
from lightly_studio.models.annotation.links import AnnotationTagLinkTable
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
    # Find annotation_ids to delete
    annotations = annotation_resolver.get_all(
        session,
        filters=AnnotationsFilter(
            annotation_label_ids=annotation_label_ids,
        ),
    ).annotations
    for annotation in annotations:
        if annotation.object_detection_details:
            session.delete(annotation.object_detection_details)
        if annotation.segmentation_details:
            session.delete(annotation.segmentation_details)
    annotation_ids = [annotation.sample_id for annotation in annotations]
    # TODO(Horatiu, 06/2025): Check if there is a way to delete the links
    # automatically using SQLModel/SQLAlchemy.
    if annotation_ids:
        # Delete tag links first
        session.exec(  # type: ignore
            delete(AnnotationTagLinkTable).where(
                col(AnnotationTagLinkTable.annotation_sample_id).in_(annotation_ids)
            )
        )
        session.commit()
        # Now delete the annotations themselves
        session.exec(  # type: ignore
            delete(AnnotationBaseTable).where(
                col(AnnotationBaseTable.sample_id).in_(annotation_ids)
            )
        )
        session.commit()
