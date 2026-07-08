"""Get annotations of a given type from an annotation collection for parent samples."""

from __future__ import annotations

from collections.abc import Sequence
from uuid import UUID

from sqlalchemy.orm import joinedload
from sqlmodel import Session, col, select

from lightly_studio.database import db_array
from lightly_studio.models.annotation.annotation_base import AnnotationBaseTable, AnnotationType
from lightly_studio.models.sample import SampleTable


def get_all_by_collection_id_and_parent_sample_ids(
    session: Session,
    parent_sample_ids: Sequence[UUID],
    annotation_collection_id: UUID,
    annotation_type: AnnotationType,
) -> list[AnnotationBaseTable]:
    """Get annotations of a given type from an annotation collection for parent samples.

    Eagerly loads the type-specific details relationship so callers can iterate
    without triggering N+1 queries:
    - OBJECT_DETECTION: object_detection_details
    - SEGMENTATION_MASK: segmentation_details
    - CLASSIFICATION: no extra load (label_id is on AnnotationBaseTable itself)

    Args:
        session: Database session.
        parent_sample_ids: Parent sample IDs to fetch annotations for.
        annotation_collection_id: ID of the annotation collection the annotation
            samples must belong to.
        annotation_type: Annotation type to filter by.
    """
    if not parent_sample_ids:
        return []
    statement = (
        select(AnnotationBaseTable)
        .join(
            SampleTable,
            col(SampleTable.sample_id) == col(AnnotationBaseTable.sample_id),
        )
        .where(
            db_array.in_array(
                column=col(AnnotationBaseTable.parent_sample_id), values=parent_sample_ids
            )
        )
        .where(col(AnnotationBaseTable.annotation_type) == annotation_type)
        .where(col(SampleTable.collection_id) == annotation_collection_id)
    )
    if annotation_type == AnnotationType.OBJECT_DETECTION:
        statement = statement.options(joinedload(AnnotationBaseTable.object_detection_details))
    elif annotation_type == AnnotationType.SEGMENTATION_MASK:
        statement = statement.options(joinedload(AnnotationBaseTable.segmentation_details))

    return list(session.exec(statement).all())
