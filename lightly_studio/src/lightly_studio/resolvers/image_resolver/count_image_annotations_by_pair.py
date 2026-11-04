"""Count annotations per (annotation source, annotation class) pair."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy.orm import aliased
from sqlmodel import Session, col, select

from lightly_studio.models.annotation.annotation_base import AnnotationBaseTable
from lightly_studio.models.annotation_label import AnnotationLabelTable
from lightly_studio.models.image import ImageTable
from lightly_studio.models.sample import SampleTable
from lightly_studio.resolvers.image_filter import ImageFilter
from lightly_studio.resolvers.image_resolver import annotation_count_helpers
from lightly_studio.resolvers.image_resolver.annotation_count_types import (
    AnnotationCountMode,
    AnnotationPairCount,
)

_PairKey = tuple[UUID, UUID, str]


def count_image_annotations_by_pair(
    session: Session,
    collection_id: UUID,
    image_filter: ImageFilter | None = None,
    count_mode: AnnotationCountMode = AnnotationCountMode.OBJECTS,
) -> list[AnnotationPairCount]:
    """Count annotations per (annotation source, annotation class) pair.

    The annotation source is the collection of the annotation's own sample. The
    total count ignores the filter and the current count applies it. Pairs
    without any annotation are not returned.

    Args:
        session: The database session.
        collection_id: The image collection to count annotations in.
        image_filter: Filter that restricts the images for the current count.
        count_mode: Count annotation objects or distinct annotated samples.

    Returns:
        One entry per pair with a total count above zero.
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
        image_filter=image_filter,
        count_mode=count_mode,
    )
    return [
        AnnotationPairCount(
            annotation_collection_id=source_id,
            annotation_label_id=label_id,
            label_name=label_name,
            current_count=current_counts.get((source_id, label_id, label_name), 0),
            total_count=total_count,
        )
        for (source_id, label_id, label_name), total_count in total_counts.items()
        if total_count > 0
    ]


def _get_counts(
    session: Session,
    collection_id: UUID,
    image_filter: ImageFilter | None,
    count_mode: AnnotationCountMode,
) -> dict[_PairKey, int]:
    annotation_sample = aliased(SampleTable)
    query = (
        select(
            col(annotation_sample.collection_id),
            AnnotationLabelTable.annotation_label_id,
            AnnotationLabelTable.annotation_label_name,
            annotation_count_helpers.build_count_expression(count_mode).label("count"),
        )
        .join(
            AnnotationBaseTable,
            col(AnnotationBaseTable.annotation_label_id)
            == col(AnnotationLabelTable.annotation_label_id),
        )
        .join(
            annotation_sample,
            col(annotation_sample.sample_id) == col(AnnotationBaseTable.sample_id),
        )
        .join(
            ImageTable,
            col(ImageTable.sample_id) == col(AnnotationBaseTable.parent_sample_id),
        )
        .join(SampleTable, col(SampleTable.sample_id) == col(ImageTable.sample_id))
        .where(SampleTable.collection_id == collection_id)
    )
    if image_filter is not None:
        query = image_filter.apply(query)  # type: ignore[type-var]
    query = query.group_by(
        col(annotation_sample.collection_id),
        col(AnnotationLabelTable.annotation_label_id),
        col(AnnotationLabelTable.annotation_label_name),
    ).order_by(
        col(AnnotationLabelTable.annotation_label_name).asc(),
        col(annotation_sample.collection_id).asc(),
    )
    return {(row[0], row[1], row[2]): row[3] for row in session.exec(query).all()}
