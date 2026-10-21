"""Delete annotations by their IDs."""

from __future__ import annotations

from collections.abc import Sequence
from uuid import UUID

from sqlmodel import Session, SQLModel, col, delete, select

from lightly_studio.models.annotation.annotation_base import AnnotationBaseTable
from lightly_studio.models.annotation.cuboid_3d import Cuboid3DAnnotationTable
from lightly_studio.models.annotation.object_detection import ObjectDetectionAnnotationTable
from lightly_studio.models.annotation.segmentation import SegmentationAnnotationTable
from lightly_studio.models.caption import CaptionTable
from lightly_studio.models.sample import SampleTable, SampleTagLinkTable
from lightly_studio.models.sample_embedding import SampleEmbeddingTable
from lightly_studio.models.temporal_span import TemporalSpanTable
from lightly_studio.resolvers.annotation_resolver.delete_annotation import (
    delete_evaluation_metrics,
)
from lightly_studio.utils import batching


def delete_annotations_by_ids(
    session: Session,
    annotation_ids: Sequence[UUID],
) -> int:
    """Delete annotations, their samples and dependent rows.

    The delete runs in three phases with a commit after each phase. It is not atomic:
    a failure can leave a partial delete. Callers must validate the IDs before the call.
    IDs that do not exist are ignored.

    Args:
        session: Database session.
        annotation_ids: IDs of the annotations to delete.

    Returns:
        The number of deleted annotations.
    """
    parent_sample_id_by_annotation_id = _get_parent_sample_ids(
        session=session, annotation_ids=annotation_ids
    )
    existing_annotation_ids = list(parent_sample_id_by_annotation_id)
    if not existing_annotation_ids:
        return 0

    caption_sample_ids = _get_caption_sample_ids(
        session=session, parent_sample_ids=existing_annotation_ids
    )
    sample_ids = existing_annotation_ids + caption_sample_ids

    # DuckDB rejects the delete of a parent row in the transaction that deleted its child
    # rows, so each foreign key level is committed separately. PostgreSQL does not need this,
    # see delete_dataset.py.
    # TODO(Jonas, 06/2026): Replace eager deletion with explicit evaluation invalidation once
    # evaluation results can be recomputed or marked stale independently from annotation updates.
    delete_evaluation_metrics(
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
    _delete_by_sample_ids(
        session=session, tables=(AnnotationBaseTable,), sample_ids=existing_annotation_ids
    )
    session.commit()
    _delete_by_sample_ids(session=session, tables=(SampleTable,), sample_ids=sample_ids)
    session.commit()
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


def _get_caption_sample_ids(session: Session, parent_sample_ids: Sequence[UUID]) -> list[UUID]:
    caption_sample_ids: list[UUID] = []
    for batch in batching.batched(items=parent_sample_ids):
        caption_sample_ids.extend(
            session.exec(
                select(CaptionTable.sample_id).where(col(CaptionTable.parent_sample_id).in_(batch))
            ).all()
        )
    return caption_sample_ids


def _delete_by_sample_ids(
    session: Session, tables: Sequence[type[SQLModel]], sample_ids: Sequence[UUID]
) -> None:
    for table in tables:
        sample_id_column = col(table.sample_id)  # type: ignore[attr-defined]
        for batch in batching.batched(items=sample_ids):
            session.exec(delete(table).where(sample_id_column.in_(batch)))
