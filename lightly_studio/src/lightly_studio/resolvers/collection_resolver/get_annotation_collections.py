"""Implementation of the get annotation collections resolver function."""

from __future__ import annotations

from uuid import UUID

from sqlmodel import Session, col, select

from lightly_studio.models.collection import CollectionTable, SampleType


def get_annotation_collections(
    session: Session,
    parent_collection_id: UUID,
) -> list[CollectionTable]:
    """Retrieves all annotation collections under a given parent collection.

    Args:
        session:
            The database session to use.
        parent_collection_id:
            The UUID of the parent collection.

    Returns:
        Annotation collections that are direct children of the parent
        collection, ordered by creation time ascending.
    """
    statement = (
        select(CollectionTable)
        .where(col(CollectionTable.parent_collection_id) == parent_collection_id)
        .where(CollectionTable.sample_type == SampleType.ANNOTATION)
        .order_by(col(CollectionTable.created_at).asc())
    )
    return list(session.exec(statement).all())
