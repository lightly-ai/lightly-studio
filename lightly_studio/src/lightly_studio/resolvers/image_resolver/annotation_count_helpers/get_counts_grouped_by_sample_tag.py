"""Query annotation counts grouped by sample tag and label."""

from __future__ import annotations

from uuid import UUID

from sqlmodel import Session, col

from lightly_studio.models.annotation.annotation_base import AnnotationBaseTable, AnnotationType
from lightly_studio.models.annotation_label import AnnotationLabelTable
from lightly_studio.models.sample import SampleTagLinkTable
from lightly_studio.resolvers.image_filter import ImageFilter
from lightly_studio.resolvers.image_resolver.annotation_count_types import AnnotationCountMode

from .build_grouped_count_query import build_grouped_count_query
from .restrict_to_annotation_sources import restrict_to_annotation_sources


def get_counts_grouped_by_sample_tag(  # noqa: PLR0913
    session: Session,
    collection_id: UUID,
    sample_tag_ids: list[UUID],
    image_filter: ImageFilter | None,
    annotation_type: AnnotationType | None,
    annotation_collection_ids: list[UUID] | None,
    count_mode: AnnotationCountMode,
) -> dict[tuple[UUID, str], int]:
    """Return annotation counts keyed by (tag_id, label_name)."""
    query = build_grouped_count_query(collection_id, sample_tag_ids, count_mode)
    if annotation_type is not None:
        query = query.where(col(AnnotationBaseTable.annotation_type) == annotation_type)
    if annotation_collection_ids:
        query = restrict_to_annotation_sources(query, annotation_collection_ids)
    if image_filter is not None:
        query = image_filter.apply(query)  # type: ignore[type-var]
    query = query.group_by(
        col(SampleTagLinkTable.tag_id),
        AnnotationLabelTable.annotation_label_name,
    )
    result: dict[tuple[UUID, str], int] = {}
    for tag_id, label_name, count in session.exec(query).all():
        assert tag_id is not None
        result[(tag_id, label_name)] = count
    return result
