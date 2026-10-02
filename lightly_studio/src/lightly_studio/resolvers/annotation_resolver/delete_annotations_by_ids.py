"""Delete many annotations of one annotation collection by their IDs."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any
from uuid import UUID

from sqlalchemy.orm import Mapped
from sqlmodel import Session, SQLModel, col, delete, select

from lightly_studio.models.annotation.annotation_base import AnnotationBaseTable
from lightly_studio.models.annotation.cuboid_3d import Cuboid3DAnnotationTable
from lightly_studio.models.annotation.object_detection import ObjectDetectionAnnotationTable
from lightly_studio.models.annotation.segmentation import SegmentationAnnotationTable
from lightly_studio.models.metadata import SampleMetadataTable
from lightly_studio.models.sample import SampleTable, SampleTagLinkTable
from lightly_studio.models.sample_embedding import SampleEmbeddingTable
from lightly_studio.models.temporal_span import TemporalSpanTable
from lightly_studio.resolvers.annotation_resolver.delete_annotation import (
    delete_evaluation_metrics,
)
from lightly_studio.utils import batching


def delete_annotations_by_ids(
    session: Session,
    annotation_collection_id: UUID,
    annotation_ids: Sequence[UUID],
) -> int:
    """Delete annotations, their detail rows and their samples.

    Only annotations in the given annotation collection are deleted. IDs of annotations in other
    collections and unknown IDs are ignored. Rows are deleted in foreign-key-safe order
    (child -> parent), because no foreign key has ``ON DELETE CASCADE``.

    Args:
        session: Database session.
        annotation_collection_id: ID of the annotation collection that the annotations belong to.
        annotation_ids: IDs of the annotations to delete.

    Returns:
        The number of deleted annotations.
    """
    rows = _get_annotation_and_parent_ids(
        session=session,
        annotation_collection_id=annotation_collection_id,
        annotation_ids=annotation_ids,
    )
    if not rows:
        return 0
    ids = [annotation_id for annotation_id, _ in rows]
    parent_sample_ids = list({parent_sample_id for _, parent_sample_id in rows})

    # Evaluation metrics reference the annotations, so they are deleted first.
    delete_evaluation_metrics(
        session=session, annotation_ids=ids, parent_sample_ids=parent_sample_ids
    )
    _delete_annotation_rows(session=session, annotation_ids=ids)
    _delete_annotation_samples(session=session, sample_ids=ids)
    return len(ids)


def _get_annotation_and_parent_ids(
    session: Session,
    annotation_collection_id: UUID,
    annotation_ids: Sequence[UUID],
) -> list[tuple[UUID, UUID]]:
    rows: list[tuple[UUID, UUID]] = []
    for batch in batching.batched(items=annotation_ids):
        rows.extend(
            session.exec(
                select(AnnotationBaseTable.sample_id, AnnotationBaseTable.parent_sample_id)
                .join(AnnotationBaseTable.sample)
                .where(col(SampleTable.collection_id) == annotation_collection_id)
                .where(col(AnnotationBaseTable.sample_id).in_(batch))
            ).all()
        )
    return rows


def _delete_annotation_rows(session: Session, annotation_ids: list[UUID]) -> None:
    _delete_by_sample_ids(
        session=session,
        table=ObjectDetectionAnnotationTable,
        sample_id_column=col(ObjectDetectionAnnotationTable.sample_id),
        sample_ids=annotation_ids,
    )
    _delete_by_sample_ids(
        session=session,
        table=SegmentationAnnotationTable,
        sample_id_column=col(SegmentationAnnotationTable.sample_id),
        sample_ids=annotation_ids,
    )
    _delete_by_sample_ids(
        session=session,
        table=Cuboid3DAnnotationTable,
        sample_id_column=col(Cuboid3DAnnotationTable.sample_id),
        sample_ids=annotation_ids,
    )
    _delete_by_sample_ids(
        session=session,
        table=TemporalSpanTable,
        sample_id_column=col(TemporalSpanTable.sample_id),
        sample_ids=annotation_ids,
    )
    # DuckDB validates foreign keys against committed state, so child deletes must be committed
    # before deleting their parent rows. PostgreSQL also supports these intermediate commits.
    session.commit()
    _delete_by_sample_ids(
        session=session,
        table=AnnotationBaseTable,
        sample_id_column=col(AnnotationBaseTable.sample_id),
        sample_ids=annotation_ids,
    )
    session.commit()


def _delete_annotation_samples(session: Session, sample_ids: list[UUID]) -> None:
    _delete_by_sample_ids(
        session=session,
        table=SampleTagLinkTable,
        sample_id_column=col(SampleTagLinkTable.sample_id),
        sample_ids=sample_ids,
    )
    _delete_by_sample_ids(
        session=session,
        table=SampleEmbeddingTable,
        sample_id_column=col(SampleEmbeddingTable.sample_id),
        sample_ids=sample_ids,
    )
    _delete_by_sample_ids(
        session=session,
        table=SampleMetadataTable,
        sample_id_column=col(SampleMetadataTable.sample_id),
        sample_ids=sample_ids,
    )
    session.commit()
    _delete_by_sample_ids(
        session=session,
        table=SampleTable,
        sample_id_column=col(SampleTable.sample_id),
        sample_ids=sample_ids,
    )
    session.commit()


def _delete_by_sample_ids(
    session: Session,
    table: type[SQLModel],
    sample_id_column: Mapped[Any],
    sample_ids: list[UUID],
) -> None:
    for batch in batching.batched(items=sample_ids):
        session.exec(delete(table).where(sample_id_column.in_(batch)))
