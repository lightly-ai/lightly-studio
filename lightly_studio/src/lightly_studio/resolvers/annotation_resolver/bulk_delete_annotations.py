"""Bulk-delete annotations scoped to one annotation collection."""

from __future__ import annotations

from uuid import UUID

from sqlmodel import Session, col, delete, select

from lightly_studio.models.annotation.annotation_base import AnnotationBaseTable
from lightly_studio.models.annotation.object_detection import ObjectDetectionAnnotationTable
from lightly_studio.models.annotation.segmentation import SegmentationAnnotationTable
from lightly_studio.models.sample import SampleTable, SampleTagLinkTable
from lightly_studio.models.sample_embedding import SampleEmbeddingTable
from lightly_studio.models.temporal_span import TemporalSpanTable
from lightly_studio.resolvers.annotation_resolver.delete_annotation import delete_evaluation_metrics
from lightly_studio.resolvers.annotations.annotations_filter import AnnotationsFilter
from lightly_studio.resolvers.evaluation_run_resolver import mark_stale_by_collection_id
from lightly_studio.utils import batching


def bulk_delete_annotations(
    session: Session,
    collection_id: UUID,
    annotation_ids: list[UUID],
) -> int:
    """Delete annotations after validating all ids belong to the collection."""
    unique_annotation_ids = list(dict.fromkeys(annotation_ids))
    if not unique_annotation_ids:
        return 0

    scoped_annotation_ids = _get_scoped_annotation_ids(
        session=session,
        collection_id=collection_id,
        annotation_ids=unique_annotation_ids,
    )
    if scoped_annotation_ids != set(unique_annotation_ids):
        raise ValueError("Some annotations are not in the requested collection.")

    parent_sample_ids = _get_parent_sample_ids(
        session=session,
        annotation_ids=unique_annotation_ids,
    )
    delete_evaluation_metrics(
        session=session,
        annotation_ids=unique_annotation_ids,
        parent_sample_ids=parent_sample_ids,
    )
    _delete_detail_rows(session=session, annotation_ids=unique_annotation_ids)
    session.commit()

    _delete_annotation_base_rows(session=session, annotation_ids=unique_annotation_ids)
    session.commit()

    _delete_annotation_sample_children(session=session, annotation_ids=unique_annotation_ids)
    session.commit()

    _delete_annotation_samples(session=session, annotation_ids=unique_annotation_ids)
    session.commit()

    deleted_count = len(unique_annotation_ids)
    mark_stale_by_collection_id(session=session, collection_id=collection_id)
    return deleted_count


def _get_scoped_annotation_ids(
    session: Session,
    collection_id: UUID,
    annotation_ids: list[UUID],
) -> set[UUID]:
    filters = AnnotationsFilter(sample_ids=annotation_ids, collection_ids=[collection_id])
    query = filters.build_sample_ids_query(collection_id=collection_id)
    return set(session.exec(query).all())


def _get_parent_sample_ids(session: Session, annotation_ids: list[UUID]) -> list[UUID]:
    parent_sample_ids: list[UUID] = []
    for annotation_id_batch in batching.batched(annotation_ids):
        parent_sample_ids.extend(
            session.exec(
                select(AnnotationBaseTable.parent_sample_id).where(
                    col(AnnotationBaseTable.sample_id).in_(annotation_id_batch)
                )
            ).all()
        )
    return parent_sample_ids


def _delete_detail_rows(session: Session, annotation_ids: list[UUID]) -> None:
    for annotation_id_batch in batching.batched(annotation_ids):
        session.exec(
            delete(ObjectDetectionAnnotationTable).where(
                col(ObjectDetectionAnnotationTable.sample_id).in_(annotation_id_batch)
            )
        )
        session.exec(
            delete(SegmentationAnnotationTable).where(
                col(SegmentationAnnotationTable.sample_id).in_(annotation_id_batch)
            )
        )
        session.exec(
            delete(TemporalSpanTable).where(col(TemporalSpanTable.sample_id).in_(annotation_id_batch))
        )


def _delete_annotation_base_rows(session: Session, annotation_ids: list[UUID]) -> None:
    for annotation_id_batch in batching.batched(annotation_ids):
        session.exec(
            delete(AnnotationBaseTable).where(
                col(AnnotationBaseTable.sample_id).in_(annotation_id_batch)
            )
        )


def _delete_annotation_sample_children(session: Session, annotation_ids: list[UUID]) -> None:
    for annotation_id_batch in batching.batched(annotation_ids):
        session.exec(
            delete(SampleTagLinkTable).where(
                col(SampleTagLinkTable.sample_id).in_(annotation_id_batch)
            )
        )
        session.exec(
            delete(SampleEmbeddingTable).where(
                col(SampleEmbeddingTable.sample_id).in_(annotation_id_batch)
            )
        )


def _delete_annotation_samples(session: Session, annotation_ids: list[UUID]) -> None:
    for annotation_id_batch in batching.batched(annotation_ids):
        session.exec(
            delete(SampleTable).where(col(SampleTable.sample_id).in_(annotation_id_batch))
        )
