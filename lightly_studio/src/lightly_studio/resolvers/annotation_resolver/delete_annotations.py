"""Handler for database operations related to annotations."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import or_
from sqlmodel import Session, col, delete

from lightly_studio.models.annotation.annotation_base import (
    AnnotationBaseTable,
)
from lightly_studio.models.evaluation_annotation_metric import EvaluationAnnotationMetricTable
from lightly_studio.models.evaluation_sample_metric import EvaluationSampleMetricTable
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
    parent_sample_ids = list({annotation.parent_sample_id for annotation in annotations})
    if annotation_ids:
        # TODO(Jonas, 06/2026): Replace eager deletion with explicit evaluation invalidation
        # once evaluation results can be recomputed or marked stale independently.
        session.exec(
            delete(EvaluationAnnotationMetricTable).where(
                or_(
                    col(EvaluationAnnotationMetricTable.pred_annotation_id).in_(annotation_ids),
                    col(EvaluationAnnotationMetricTable.gt_annotation_id).in_(annotation_ids),
                )
            )
        )
        session.exec(
            delete(EvaluationSampleMetricTable).where(
                col(EvaluationSampleMetricTable.sample_id).in_(parent_sample_ids)
            )
        )
        session.exec(
            delete(AnnotationBaseTable).where(
                col(AnnotationBaseTable.sample_id).in_(annotation_ids)
            )
        )
        session.commit()
