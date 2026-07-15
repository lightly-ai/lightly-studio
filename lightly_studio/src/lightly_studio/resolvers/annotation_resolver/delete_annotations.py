"""Handler for database operations related to annotations."""

from __future__ import annotations

from uuid import UUID

from sqlmodel import Session, col, delete

from lightly_studio.models.annotation.annotation_base import (
    AnnotationBaseTable,
)
from lightly_studio.resolvers import annotation_resolver
from lightly_studio.resolvers.annotation_resolver.delete_annotation import (
    delete_evaluation_metrics,
)
from lightly_studio.resolvers.annotations.annotations_filter import (
    AnnotationsFilter,
)
from lightly_studio.utils import batching


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
        if annotation.temporal_span_details:
            session.delete(annotation.temporal_span_details)
    session.commit()

    # Now delete the annotations themselves
    annotation_ids = [annotation.sample_id for annotation in annotations]
    parent_sample_ids = list({annotation.parent_sample_id for annotation in annotations})
    if annotation_ids:
        # TODO(Jonas, 06/2026): Replace eager deletion with explicit evaluation invalidation
        # once evaluation results can be recomputed or marked stale independently.
        delete_evaluation_metrics(
            session=session,
            annotation_ids=annotation_ids,
            parent_sample_ids=parent_sample_ids,
        )
    for batch in batching.batched(items=annotation_ids):
        session.exec(
            delete(AnnotationBaseTable).where(col(AnnotationBaseTable.sample_id).in_(batch))
        )
    session.commit()
