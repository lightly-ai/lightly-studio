"""Query total annotation counts per label for a collection."""

from __future__ import annotations

from uuid import UUID

from sqlmodel import Session, col

from lightly_studio.models.annotation.annotation_base import AnnotationType
from lightly_studio.models.annotation_label import AnnotationLabelTable
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
    label_name = col(AnnotationLabelTable.annotation_label_name)
    query = annotation_count_helpers.build_label_count_query(
        collection_id=collection_id,
        key_columns=[label_name],
        count_mode=count_mode,
        annotation_type=annotation_type,
        annotation_collection_ids=annotation_collection_ids,
    ).order_by(label_name.asc())
    return {row[0]: row[1] for row in session.exec(query).all()}
