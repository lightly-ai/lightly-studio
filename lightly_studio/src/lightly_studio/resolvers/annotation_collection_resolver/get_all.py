"""Query annotation collections for a dataset."""

from __future__ import annotations

from uuid import UUID

from sqlmodel import Session, col, select

from lightly_studio.models.annotation_collection import AnnotationCollectionTable


def get_all(
    session: Session,
    dataset_id: UUID,
) -> list[AnnotationCollectionTable]:
    """Return all annotation collections for a dataset, ordered by creation time."""
    stmt = (
        select(AnnotationCollectionTable)
        .where(col(AnnotationCollectionTable.dataset_id) == dataset_id)
        .order_by(col(AnnotationCollectionTable.created_at).asc())
    )
    return list(session.exec(stmt).all())
