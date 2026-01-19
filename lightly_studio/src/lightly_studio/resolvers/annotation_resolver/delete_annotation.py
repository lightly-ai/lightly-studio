"""Handler for database operations related to annotations."""

from __future__ import annotations

from uuid import UUID

from sqlmodel import Session, col, delete

from lightly_studio.models.annotation.annotation_base import AnnotationBaseTable
from lightly_studio.models.annotation.links import AnnotationTagLinkTable
from lightly_studio.models.annotation.object_detection import (
    ObjectDetectionAnnotationTable,
)
from lightly_studio.models.annotation.segmentation import (
    SegmentationAnnotationTable,
)
from lightly_studio.models.sample import SampleTable
from lightly_studio.resolvers import annotation_resolver


def delete_annotation(
    session: Session,
    annotation_id: UUID,
    delete_sample: bool = True,
) -> None:
    """Delete all annotations and their tag links using filters.

    Args:
        session: Database session.
        annotation_id: Annotation ID to filter by.
        delete_sample: Whether to also delete the annotation's sample. Defaults to True.
                      Set to False when updating an annotation (to reuse the sample).
    """
    # Find annotation_ids to delete
    annotation = annotation_resolver.get_by_id(
        session,
        annotation_id=annotation_id,
    )
    if not annotation:
        raise ValueError(f"Annotation {annotation_id} not found")

    # Store the annotation's sample_id before deletion
    annotation_sample_id = annotation.sample_id

    session.exec(  # type: ignore
        delete(ObjectDetectionAnnotationTable).where(
            col(ObjectDetectionAnnotationTable.sample_id) == annotation.sample_id
        )
    )
    session.exec(  # type: ignore
        delete(SegmentationAnnotationTable).where(
            col(SegmentationAnnotationTable.sample_id) == annotation.sample_id
        )
    )
    session.commit()

    # Delete tag links
    session.exec(  # type: ignore
        delete(AnnotationTagLinkTable).where(
            col(AnnotationTagLinkTable.annotation_sample_id).in_([annotation.sample_id])
        )
    )
    session.commit()

    # Delete the annotation using explicit DELETE to avoid relationship cascade issues
    session.exec(  # type: ignore
        delete(AnnotationBaseTable).where(
            col(AnnotationBaseTable.sample_id) == annotation.sample_id
        )
    )
    session.commit()

    # Then delete the annotation's sample (created specifically for this annotation)
    # unless we're keeping it for reuse (e.g., when updating annotation label)
    if delete_sample:
        annotation_sample = session.get(SampleTable, annotation_sample_id)
        if annotation_sample:
            session.delete(annotation_sample)
            session.commit()
