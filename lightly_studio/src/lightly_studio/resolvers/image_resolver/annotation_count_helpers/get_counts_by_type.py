"""Query annotation counts grouped by annotation type for a collection."""

from __future__ import annotations

from collections.abc import Sequence
from uuid import UUID

from sqlmodel import Session, col, select

from lightly_studio.models.annotation.annotation_base import AnnotationBaseTable, AnnotationType
from lightly_studio.models.image import ImageTable
from lightly_studio.models.sample import SampleTable
from lightly_studio.resolvers.image_filter import ImageFilter
from lightly_studio.resolvers.image_resolver import annotation_count_helpers
from lightly_studio.resolvers.image_resolver.annotation_count_types import AnnotationCountMode


def get_counts_by_type(
    session: Session,
    collection_id: UUID,
    image_filter: ImageFilter | None = None,
    annotation_collection_ids: Sequence[UUID] | None = None,
    count_mode: AnnotationCountMode = AnnotationCountMode.OBJECTS,
) -> dict[AnnotationType, int]:
    """Return annotation counts per annotation type for the collection.

    The same query serves the total and the filtered count: pass ``image_filter=None`` for the
    total, and the active filter for the count of what the current view leaves visible.

    Args:
        session: Database session.
        collection_id: Collection whose images are counted.
        image_filter: Active image filter, or None for unfiltered totals.
        annotation_collection_ids: Restrict counting to these annotation sources.
        count_mode: Count annotation objects, or distinct annotated samples.

    Returns:
        Count per annotation type. Types with no matching annotations are absent.
    """
    query = (
        select(
            AnnotationBaseTable.annotation_type,
            annotation_count_helpers.build_count_expression(count_mode).label("count"),
        )
        .join(
            ImageTable,
            col(ImageTable.sample_id) == col(AnnotationBaseTable.parent_sample_id),
        )
        .join(
            SampleTable,
            col(SampleTable.sample_id) == col(ImageTable.sample_id),
        )
        .where(SampleTable.collection_id == collection_id)
    )
    if annotation_collection_ids:
        query = annotation_count_helpers.restrict_to_annotation_sources(
            query=query,
            annotation_collection_ids=list(annotation_collection_ids),
        )
    if image_filter is not None:
        query = image_filter.apply(query)
    query = query.group_by(col(AnnotationBaseTable.annotation_type))
    # The driver hands the grouping key back as its stored string, so re-wrap it in the enum.
    return {AnnotationType(row[0]): row[1] for row in session.exec(query).all()}
