"""Implementation of count_objects_by_sample_ids for annotation resolver."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any
from uuid import UUID

from sqlmodel import Session, col, func, select, union_all
from sqlmodel.sql.expression import Select

from lightly_studio.models.annotation.annotation_base import AnnotationBaseTable
from lightly_studio.models.sample import SampleTable
from lightly_studio.models.sequence import SampleSequenceLinkTable


def count_objects_by_sample_ids(
    session: Session, collection_id: UUID, sample_ids: Sequence[UUID]
) -> dict[UUID, int]:
    """Count the objects of each sample, including the ticks of a sequence.

    A sequence sample counts the annotations on all of its ticks. Every other sample counts
    the annotations attached to it directly. Every annotation is one object, so a tracked
    object counts once per tick. All annotation sources and types count.

    Args:
        session: The database session.
        collection_id: The collection the samples belong to. Samples outside it count 0.
        sample_ids: The samples to count.

    Returns:
        The object count of each requested sample, 0 for samples without objects.
    """
    if not sample_ids:
        return {}
    in_collection = (
        select(col(SampleTable.sample_id))
        .where(col(SampleTable.collection_id) == collection_id)
        .where(col(SampleTable.sample_id).in_(sample_ids))
        .scalar_subquery()
    )
    direct: Select[tuple[Any, Any]] = select(
        col(AnnotationBaseTable.parent_sample_id).label("sample_id"),
        col(AnnotationBaseTable.sample_id).label("annotation_id"),
    ).where(col(AnnotationBaseTable.parent_sample_id).in_(in_collection))
    on_ticks: Select[tuple[Any, Any]] = (
        select(
            col(SampleSequenceLinkTable.sequence_sample_id).label("sample_id"),
            col(AnnotationBaseTable.sample_id).label("annotation_id"),
        )
        .join(
            AnnotationBaseTable,
            col(AnnotationBaseTable.parent_sample_id) == col(SampleSequenceLinkTable.sample_id),
        )
        .where(col(SampleSequenceLinkTable.sequence_sample_id).in_(in_collection))
    )
    objects = union_all(direct, on_ticks).subquery()
    rows = session.exec(
        select(objects.c.sample_id, func.count(objects.c.annotation_id)).group_by(
            objects.c.sample_id
        )
    ).all()
    counts = dict(rows)
    return {sample_id: counts.get(sample_id, 0) for sample_id in sample_ids}
