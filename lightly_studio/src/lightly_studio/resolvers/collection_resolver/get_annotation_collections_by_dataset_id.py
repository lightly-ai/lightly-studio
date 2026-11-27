"""Implementation of the get annotation collections by dataset ID resolver function."""

from __future__ import annotations

from uuid import UUID

from sqlmodel import Session, col, select

from lightly_studio.models.collection import CollectionTable, SampleType


def get_annotation_collections_by_dataset_id(
    session: Session,
    dataset_id: UUID,
) -> list[CollectionTable]:
    """Retrieves all annotation collections of a dataset.

    A dataset can keep annotation collections at more than one level, for example under its
    video collection and under the video frame collection. This returns all of them.

    Args:
        session:
            The database session to use.
        dataset_id:
            The ID of the dataset.

    Returns:
        Annotation collections of the dataset, ordered by creation time ascending.
    """
    statement = (
        select(CollectionTable)
        .where(col(CollectionTable.dataset_id) == dataset_id)
        .where(CollectionTable.sample_type == SampleType.ANNOTATION)
        .order_by(col(CollectionTable.created_at).asc())
    )
    return list(session.exec(statement).all())
