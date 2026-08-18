"""Query annotation counts grouped by sample tag and label."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlmodel import Session, col, select

from lightly_studio.database import db_array
from lightly_studio.models.annotation.annotation_base import AnnotationBaseTable, AnnotationType
from lightly_studio.models.annotation_label import AnnotationLabelTable
from lightly_studio.models.image import ImageTable
from lightly_studio.models.sample import SampleTable, SampleTagLinkTable
from lightly_studio.resolvers.image_filter import ImageFilter
from lightly_studio.resolvers.image_resolver.annotation_count_types import AnnotationCountMode

from .build_count_expression import build_count_expression
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
    query: Any = (
        select(
            SampleTagLinkTable.tag_id,
            AnnotationLabelTable.annotation_label_name,
            build_count_expression(count_mode).label("count"),
        )
        .join(
            AnnotationBaseTable,
            col(AnnotationBaseTable.annotation_label_id)
            == col(AnnotationLabelTable.annotation_label_id),
        )
        .join(
            ImageTable,
            col(ImageTable.sample_id) == col(AnnotationBaseTable.parent_sample_id),
        )
        .join(SampleTable, col(SampleTable.sample_id) == col(ImageTable.sample_id))
        .join(
            SampleTagLinkTable,
            col(SampleTagLinkTable.sample_id) == col(SampleTable.sample_id),
        )
        .where(
            col(SampleTable.collection_id) == collection_id,
            db_array.in_array(column=col(SampleTagLinkTable.tag_id), values=sample_tag_ids),
        )
    )
    if annotation_type is not None:
        query = query.where(col(AnnotationBaseTable.annotation_type) == annotation_type)
    if annotation_collection_ids:
        query = restrict_to_annotation_sources(query, annotation_collection_ids)
    if image_filter is not None:
        query = image_filter.apply(query)
    query = query.group_by(
        col(SampleTagLinkTable.tag_id),
        AnnotationLabelTable.annotation_label_name,
    )
    result: dict[tuple[UUID, str], int] = {}
    for tag_id, label_name, count in session.exec(query).all():
        assert tag_id is not None
        result[(tag_id, label_name)] = count
    return result
