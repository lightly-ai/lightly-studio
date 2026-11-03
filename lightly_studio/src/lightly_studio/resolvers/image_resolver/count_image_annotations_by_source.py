"""Count image annotations per annotation source and annotation class."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy.orm import aliased
from sqlmodel import Session, col
from sqlmodel.sql.expression import Select

from lightly_studio.models.annotation.annotation_base import AnnotationBaseTable
from lightly_studio.models.annotation_label import AnnotationLabelTable
from lightly_studio.models.sample import SampleTable
from lightly_studio.resolvers.image_filter import ImageFilter
from lightly_studio.resolvers.image_resolver import annotation_count_helpers
from lightly_studio.resolvers.image_resolver.annotation_count_types import (
    AnnotationCountMode,
    SourceLabelCount,
)

_PairKey = tuple[UUID, UUID, str]


def count_image_annotations_by_source(
    session: Session,
    collection_id: UUID,
    image_filter: ImageFilter | None = None,
    count_mode: AnnotationCountMode = AnnotationCountMode.SAMPLES,
) -> list[SourceLabelCount]:
    """Count the annotations of an image collection per annotation source and class.

    The current counts apply the filter without its own `source_label_pairs`, so ticking
    a pair does not shrink the counts of the other pairs.
    """
    annotation_count_helpers.resolve_embedding_region(
        session=session,
        collection_id=collection_id,
        image_filter=image_filter,
    )
    total_counts = _get_counts(
        session=session,
        collection_id=collection_id,
        image_filter=None,
        count_mode=count_mode,
    )
    current_counts = _get_counts(
        session=session,
        collection_id=collection_id,
        image_filter=_without_pairs(image_filter=image_filter),
        count_mode=count_mode,
    )
    return [
        SourceLabelCount(
            annotation_collection_id=source_id,
            annotation_label_id=label_id,
            label_name=label_name,
            current_count=current_counts.get((source_id, label_id, label_name), 0),
            total_count=total_count,
        )
        for (source_id, label_id, label_name), total_count in total_counts.items()
    ]


def _get_counts(
    session: Session,
    collection_id: UUID,
    image_filter: ImageFilter | None,
    count_mode: AnnotationCountMode,
) -> dict[_PairKey, int]:
    annotation_sample = aliased(SampleTable)
    key_columns: list[Any] = [
        col(annotation_sample.collection_id),
        col(AnnotationLabelTable.annotation_label_id),
        col(AnnotationLabelTable.annotation_label_name),
    ]
    query: Select[Any] = annotation_count_helpers.build_label_count_query(
        collection_id=collection_id,
        key_columns=key_columns,
        count_mode=count_mode,
    ).join(
        annotation_sample,
        col(annotation_sample.sample_id) == col(AnnotationBaseTable.sample_id),
    )
    if image_filter is not None:
        query = image_filter.apply(query)
    query = query.order_by(col(AnnotationLabelTable.annotation_label_name).asc())
    return {(row[0], row[1], row[2]): row[3] for row in session.exec(query).all()}


def _without_pairs(image_filter: ImageFilter | None) -> ImageFilter | None:
    sample_filter = image_filter.sample_filter if image_filter is not None else None
    if image_filter is None or sample_filter is None or sample_filter.annotations_filter is None:
        return image_filter
    annotations_filter = sample_filter.annotations_filter.model_copy(
        update={"source_label_pairs": None}
    )
    return image_filter.model_copy(
        update={
            "sample_filter": sample_filter.model_copy(
                update={"annotations_filter": annotations_filter}
            )
        }
    )
