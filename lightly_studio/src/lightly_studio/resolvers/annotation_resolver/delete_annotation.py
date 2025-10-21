"""Handler for database operations related to annotations."""

from __future__ import annotations

from uuid import UUID

from sqlmodel import Session, col, delete

from lightly_studio.models.annotation.links import AnnotationTagLinkTable
from lightly_studio.resolvers import annotation_resolver


def delete_annotation(
    session: Session,
    annotation_id: UUID,
) -> None:
    """Delete all annotations and their tag links using filters.

    Args:
        session: Database session.
        annotation_id: Annotation ID to filter by.
    """
    # Find annotation_ids to delete
    annotation = annotation_resolver.get_by_id(
        session,
        annotation_id=annotation_id,
    )
    if not annotation:
        raise ValueError(f"Annotation {annotation_id} not found")
    if annotation.object_detection_details:
        session.delete(annotation.object_detection_details)
    if annotation.instance_segmentation_details:
        session.delete(annotation.instance_segmentation_details)
    if annotation.semantic_segmentation_details:
        session.delete(annotation.semantic_segmentation_details)

    session.exec(  # type: ignore
        delete(AnnotationTagLinkTable).where(
            col(AnnotationTagLinkTable.annotation_id).in_([annotation.annotation_id])
        )
    )

    session.commit()
    session.delete(annotation)
    session.commit()
