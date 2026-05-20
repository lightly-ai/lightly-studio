"""Get annotation labels used in a specific annotation collection."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy.orm import aliased
from sqlmodel import Session, col, select

from lightly_studio.models.annotation.annotation_base import AnnotationBaseTable
from lightly_studio.models.annotation_label import AnnotationLabelTable
from lightly_studio.models.sample import SampleTable


def get_by_annotation_collection(
    session: Session,
    annotation_collection_id: UUID,
) -> list[AnnotationLabelTable]:
    """Return distinct annotation labels used in the given annotation collection.

    Args:
        session: The database session.
        annotation_collection_id: The collection_id of the annotation collection
            (i.e. sample.collection_id for annotation samples).

    Returns:
        Distinct annotation labels present in the collection, ordered alphabetically.
    """
    annotation_sample = aliased(SampleTable)
    labels = session.exec(
        select(AnnotationLabelTable)
        .join(
            AnnotationBaseTable,
            AnnotationBaseTable.annotation_label_id == AnnotationLabelTable.annotation_label_id,  # type: ignore[arg-type]
        )
        .join(annotation_sample, AnnotationBaseTable.sample_id == annotation_sample.sample_id)  # type: ignore[arg-type]
        .where(annotation_sample.collection_id == annotation_collection_id)
        .distinct()
        .order_by(col(AnnotationLabelTable.annotation_label_name).asc())
    ).all()
    return list(labels)
