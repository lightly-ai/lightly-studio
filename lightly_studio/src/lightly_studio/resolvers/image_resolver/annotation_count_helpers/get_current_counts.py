"""Query filtered annotation counts per label for a collection."""

from __future__ import annotations

from uuid import UUID

from sqlmodel import Session, col, select

from lightly_studio.models.annotation.annotation_base import AnnotationBaseTable, AnnotationType
from lightly_studio.models.annotation_label import AnnotationLabelTable
from lightly_studio.models.image import ImageTable
from lightly_studio.models.sample import SampleTable
from lightly_studio.resolvers.image_filter import ImageFilter
from lightly_studio.resolvers.image_resolver.annotation_count_types import AnnotationCountMode

from .build_count_expression import build_count_expression
from .restrict_to_annotation_sources import restrict_to_annotation_sources


def get_current_counts(  # noqa: PLR0913
    session: Session,
    collection_id: UUID,
    image_filter: ImageFilter | None,
    annotation_type: AnnotationType | None = None,
    annotation_collection_ids: list[UUID] | None = None,
    count_mode: AnnotationCountMode = AnnotationCountMode.OBJECTS,
) -> dict[str, int]:
    """Return filtered annotation counts per label for the collection."""
    query = (
        select(
            AnnotationLabelTable.annotation_label_name,
            build_count_expression(count_mode).label("current_count"),
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
        .join(
            SampleTable,
            col(SampleTable.sample_id) == col(ImageTable.sample_id),
        )
        .where(SampleTable.collection_id == collection_id)
    )
    if annotation_type is not None:
        query = query.where(col(AnnotationBaseTable.annotation_type) == annotation_type)
    if annotation_collection_ids:
        query = restrict_to_annotation_sources(query, annotation_collection_ids)
    if image_filter is not None:
        query = image_filter.apply(query)
    query = query.group_by(AnnotationLabelTable.annotation_label_name).order_by(
        col(AnnotationLabelTable.annotation_label_name).asc()
    )
    return {row[0]: row[1] for row in session.exec(query).all()}
