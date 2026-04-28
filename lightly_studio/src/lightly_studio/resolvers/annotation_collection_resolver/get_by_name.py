"""Look up an annotation collection by name within a dataset."""

from __future__ import annotations

from uuid import UUID

from sqlmodel import Session, col, select

from lightly_studio.models.annotation_collection import AnnotationCollectionTable


def get_by_name(
    session: Session,
    dataset_id: UUID,
    name: str,
) -> AnnotationCollectionTable | None:
    """Return the annotation collection with the given name, or None."""
    stmt = (
        select(AnnotationCollectionTable)
        .where(col(AnnotationCollectionTable.dataset_id) == dataset_id)
        .where(col(AnnotationCollectionTable.name) == name)
    )
    return session.exec(stmt).first()
