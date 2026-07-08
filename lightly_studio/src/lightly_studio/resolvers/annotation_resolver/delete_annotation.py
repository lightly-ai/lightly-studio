"""Handler for database operations related to annotations."""

from __future__ import annotations

from uuid import UUID

import sqlalchemy
from sqlmodel import Session, col, delete, select

from lightly_studio.models.annotation.annotation_base import AnnotationBaseTable
from lightly_studio.models.annotation.object_detection import (
    ObjectDetectionAnnotationTable,
)
from lightly_studio.models.annotation.segmentation import (
    SegmentationAnnotationTable,
)
from lightly_studio.models.evaluation_annotation_metric import EvaluationAnnotationMetricTable
from lightly_studio.models.evaluation_sample_metric import EvaluationSampleMetricTable
from lightly_studio.models.sample import SampleTable, SampleTagLinkTable
from lightly_studio.models.sample_embedding import SampleEmbeddingTable
from lightly_studio.resolvers import annotation_resolver
from lightly_studio.utils import batching


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

    # TODO(Jonas, 06/2026): Replace eager deletion with explicit evaluation invalidation once
    # evaluation results can be recomputed or marked stale independently from annotation updates.
    delete_evaluation_metrics(
        session=session,
        annotation_ids=[annotation.sample_id],
        parent_sample_ids=[annotation.parent_sample_id],
    )
    session.exec(
        delete(ObjectDetectionAnnotationTable).where(
            col(ObjectDetectionAnnotationTable.sample_id) == annotation.sample_id
        )
    )
    session.exec(
        delete(SegmentationAnnotationTable).where(
            col(SegmentationAnnotationTable.sample_id) == annotation.sample_id
        )
    )
    session.commit()

    # Delete the annotation using explicit DELETE to avoid relationship cascade issues
    session.exec(
        delete(AnnotationBaseTable).where(
            col(AnnotationBaseTable.sample_id) == annotation.sample_id
        )
    )
    session.commit()

    # Then delete the annotation's sample (created specifically for this annotation)
    # unless we're keeping it for reuse (e.g., when updating annotation label)
    if delete_sample:
        session.exec(
            delete(SampleTagLinkTable).where(
                col(SampleTagLinkTable.sample_id) == annotation_sample_id
            )
        )
        # Explicitly delete embeddings before the sample.
        session.exec(
            delete(SampleEmbeddingTable).where(
                col(SampleEmbeddingTable.sample_id) == annotation_sample_id
            )
        )
        session.commit()

        annotation_sample = session.get(SampleTable, annotation_sample_id)
        if annotation_sample:
            session.delete(annotation_sample)
            session.commit()


def delete_evaluation_metrics(
    session: Session,
    annotation_ids: list[UUID],
    parent_sample_ids: list[UUID],
) -> None:
    """Delete evaluation data invalidated by annotation deletion or mutation."""
    if not annotation_ids and not parent_sample_ids:
        return

    affected_evaluation_run_ids: set[UUID] = set()
    for annotation_id_batch in batching.batched(items=annotation_ids):
        affected_evaluation_run_ids.update(
            session.exec(
                select(EvaluationAnnotationMetricTable.evaluation_run_id)
                .where(
                    sqlalchemy.or_(
                        col(EvaluationAnnotationMetricTable.pred_annotation_id).in_(
                            annotation_id_batch
                        ),
                        col(EvaluationAnnotationMetricTable.gt_annotation_id).in_(
                            annotation_id_batch
                        ),
                    )
                )
                .distinct()
            ).all()
        )

    for annotation_id_batch in batching.batched(items=annotation_ids):
        session.exec(
            delete(EvaluationAnnotationMetricTable).where(
                sqlalchemy.or_(
                    col(EvaluationAnnotationMetricTable.pred_annotation_id).in_(
                        annotation_id_batch
                    ),
                    col(EvaluationAnnotationMetricTable.gt_annotation_id).in_(annotation_id_batch),
                )
            )
        )
    if parent_sample_ids and affected_evaluation_run_ids:
        for parent_sample_id_batch in batching.batched(items=parent_sample_ids):
            for evaluation_run_id_batch in batching.batched(items=affected_evaluation_run_ids):
                session.exec(
                    delete(EvaluationSampleMetricTable).where(
                        col(EvaluationSampleMetricTable.sample_id).in_(parent_sample_id_batch),
                        col(EvaluationSampleMetricTable.evaluation_run_id).in_(
                            evaluation_run_id_batch
                        ),
                    )
                )
