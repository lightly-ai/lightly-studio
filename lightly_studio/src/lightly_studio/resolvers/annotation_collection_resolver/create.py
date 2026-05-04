"""Create an annotation collection record."""

from __future__ import annotations

from uuid import UUID

from sqlmodel import Session

from lightly_studio.models.annotation_collection import AnnotationCollectionTable


def create(
    session: Session,
    dataset_id: UUID,
    collection_id: UUID,
    name: str,
    is_ground_truth: bool = False,
    processed_sample_count: int | None = None,
    notes: str | None = None,
) -> AnnotationCollectionTable:
    """Create and persist an AnnotationCollectionTable entry."""
    record = AnnotationCollectionTable(
        dataset_id=dataset_id,
        collection_id=collection_id,
        name=name,
        is_ground_truth=is_ground_truth,
        processed_sample_count=processed_sample_count,
        notes=notes,
    )
    session.add(record)
    session.commit()
    session.refresh(record)
    return record
