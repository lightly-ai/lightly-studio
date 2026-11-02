"""Delete annotations by their IDs."""

from __future__ import annotations

import logging
import time
from collections.abc import Sequence
from uuid import UUID

import sqlalchemy
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, SQLModel, col, delete, select

from lightly_studio.models.annotation.annotation_base import AnnotationBaseTable
from lightly_studio.models.annotation.cuboid_3d import Cuboid3DAnnotationTable
from lightly_studio.models.annotation.object_detection import ObjectDetectionAnnotationTable
from lightly_studio.models.annotation.segmentation import SegmentationAnnotationTable
from lightly_studio.models.caption import CaptionTable
from lightly_studio.models.evaluation_annotation_metric import EvaluationAnnotationMetricTable
from lightly_studio.models.evaluation_sample_metric import EvaluationSampleMetricTable
from lightly_studio.models.sample import SampleTable, SampleTagLinkTable
from lightly_studio.models.sample_embedding import SampleEmbeddingTable
from lightly_studio.models.temporal_span import TemporalSpanTable
from lightly_studio.resolvers import embedding_plot_resolver, evaluation_run_resolver
from lightly_studio.utils import batching

logger = logging.getLogger(__name__)

# DuckDB's FK constraint check on the annotation_base DELETE can produce a false
# IntegrityError when a concurrent read transaction makes the ART index report stale
# child entries (duckdb#19002). Retrying gives the concurrent reader time to finish.
_FK_RETRY_ATTEMPTS = 3
_FK_RETRY_DELAY_S = 0.1


def delete_annotations_by_ids(
    session: Session,
    annotation_ids: Sequence[UUID],
    delete_samples: bool = True,
) -> int:
    """Delete annotations, their samples and dependent rows.

    Also marks the evaluation runs of the annotation collections stale.

    The delete runs in three phases with a commit after each phase. It is not atomic:
    a failure can leave a partial delete. Callers must validate the IDs before the call.
    IDs that do not exist are ignored.

    Args:
        session: Database session.
        annotation_ids: IDs of the annotations to delete.
        delete_samples: Whether to also delete the annotation samples, their tags,
            embeddings and captions. Set to False to keep the samples for reuse,
            e.g. when an annotation is updated.

    Returns:
        The number of deleted annotations.
    """
    parent_sample_id_by_annotation_id = _get_parent_sample_ids(
        session=session, annotation_ids=annotation_ids
    )
    existing_annotation_ids = list(parent_sample_id_by_annotation_id)
    if not existing_annotation_ids:
        return 0

    sample_ids: list[UUID] = []
    if delete_samples:
        caption_sample_ids = _get_caption_sample_ids(
            session=session, parent_sample_ids=existing_annotation_ids
        )
        sample_ids = existing_annotation_ids + caption_sample_ids
    annotation_collection_ids = _get_collection_ids(
        session=session, sample_ids=existing_annotation_ids
    )

    embedding_plot_resolver.mark_dirty(session=session, sample_ids=sample_ids)

    # DuckDB rejects the delete of a parent row in the transaction that deleted its child
    # rows, so each foreign key level is committed separately. PostgreSQL does not need this,
    # see delete_dataset.py.
    # TODO(Jonas, 06/2026): Replace eager deletion with explicit evaluation invalidation once
    # evaluation results can be recomputed or marked stale independently from annotation updates.
    _delete_evaluation_metrics(
        session=session,
        annotation_ids=existing_annotation_ids,
        parent_sample_ids=list(set(parent_sample_id_by_annotation_id.values())),
    )
    _delete_by_sample_ids(
        session=session,
        tables=(
            ObjectDetectionAnnotationTable,
            SegmentationAnnotationTable,
            Cuboid3DAnnotationTable,
            TemporalSpanTable,
        ),
        sample_ids=existing_annotation_ids,
    )
    _delete_by_sample_ids(
        session=session,
        tables=(SampleTagLinkTable, SampleEmbeddingTable, TemporalSpanTable, CaptionTable),
        sample_ids=sample_ids,
    )
    session.commit()
    _delete_annotation_base_with_retry(session=session, annotation_ids=existing_annotation_ids)
    _delete_by_sample_ids(session=session, tables=(SampleTable,), sample_ids=sample_ids)
    session.commit()
    for annotation_collection_id in annotation_collection_ids:
        evaluation_run_resolver.mark_stale_by_collection_id(
            session=session, collection_id=annotation_collection_id
        )
    return len(existing_annotation_ids)


def _get_parent_sample_ids(session: Session, annotation_ids: Sequence[UUID]) -> dict[UUID, UUID]:
    """Map each existing annotation ID to its parent sample ID."""
    parent_sample_id_by_annotation_id: dict[UUID, UUID] = {}
    for batch in batching.batched(items=set(annotation_ids)):
        rows = session.exec(
            select(AnnotationBaseTable.sample_id, AnnotationBaseTable.parent_sample_id).where(
                col(AnnotationBaseTable.sample_id).in_(batch)
            )
        ).all()
        parent_sample_id_by_annotation_id.update(dict(rows))
    return parent_sample_id_by_annotation_id


def _get_collection_ids(session: Session, sample_ids: Sequence[UUID]) -> set[UUID]:
    collection_ids: set[UUID] = set()
    for batch in batching.batched(items=sample_ids):
        collection_ids.update(
            session.exec(
                select(SampleTable.collection_id)
                .where(col(SampleTable.sample_id).in_(batch))
                .distinct()
            ).all()
        )
    return collection_ids


def _get_caption_sample_ids(session: Session, parent_sample_ids: Sequence[UUID]) -> list[UUID]:
    caption_sample_ids: list[UUID] = []
    for batch in batching.batched(items=parent_sample_ids):
        caption_sample_ids.extend(
            session.exec(
                select(CaptionTable.sample_id).where(col(CaptionTable.parent_sample_id).in_(batch))
            ).all()
        )
    return caption_sample_ids


def _delete_annotation_base_with_retry(session: Session, annotation_ids: Sequence[UUID]) -> None:
    """Delete annotation_base rows, retrying on DuckDB FK false positives.

    DuckDB's FK constraint check can fail with a spurious ``IntegrityError`` when a
    concurrent read transaction makes the ART index report stale child entries
    (duckdb#19002). Retrying after a short delay gives the concurrent reader time to
    finish its transaction.
    """
    for attempt in range(_FK_RETRY_ATTEMPTS):
        try:
            _delete_by_sample_ids(
                session=session,
                tables=(AnnotationBaseTable,),
                sample_ids=annotation_ids,
            )
            session.commit()
            return
        except IntegrityError:
            session.rollback()
            if attempt + 1 >= _FK_RETRY_ATTEMPTS:
                raise
            logger.debug(
                "Retrying annotation_base delete after DuckDB FK error (attempt %d/%d)",
                attempt + 1,
                _FK_RETRY_ATTEMPTS,
            )
            time.sleep(_FK_RETRY_DELAY_S)


def _delete_by_sample_ids(
    session: Session, tables: Sequence[type[SQLModel]], sample_ids: Sequence[UUID]
) -> None:
    for table in tables:
        sample_id_column = col(table.sample_id)  # type: ignore[attr-defined]
        for batch in batching.batched(items=sample_ids):
            session.exec(delete(table).where(sample_id_column.in_(batch)))


def _delete_evaluation_metrics(
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
