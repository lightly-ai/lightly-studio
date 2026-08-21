"""Query total annotation counts per label for a collection."""

from __future__ import annotations

from uuid import UUID

from sqlmodel import Session, col, select

from lightly_studio.models.annotation.annotation_base import AnnotationBaseTable, AnnotationType
from lightly_studio.models.annotation_label import AnnotationLabelTable
from lightly_studio.models.image import ImageTable
from lightly_studio.models.sample import SampleTable
from lightly_studio.resolvers.image_resolver import annotation_count_helpers
from lightly_studio.resolvers.image_resolver.annotation_count_types import AnnotationCountMode


def get_total_counts(
    session: Session,
    collection_id: UUID,
    annotation_type: AnnotationType | None = None,
    count_mode: AnnotationCountMode = AnnotationCountMode.OBJECTS,
    annotation_collection_ids: list[UUID] | None = None,
) -> dict[str, int]:
    """Return total annotation counts per label for the collection."""
    query = (
        select(
            AnnotationLabelTable.annotation_label_name,
            annotation_count_helpers.build_count_expression(count_mode).label("total_count"),
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
        query = annotation_count_helpers.restrict_to_annotation_sources(
            query=query,
            annotation_collection_ids=annotation_collection_ids,
        )
    query = query.group_by(AnnotationLabelTable.annotation_label_name).order_by(
        col(AnnotationLabelTable.annotation_label_name).asc()
    )
    return {row[0]: row[1] for row in session.exec(query).all()}
