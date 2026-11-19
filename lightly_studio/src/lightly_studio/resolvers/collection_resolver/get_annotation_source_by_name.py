"""Implementation of the get annotation source by name resolver function."""

from __future__ import annotations

from uuid import UUID

from sqlmodel import Session, col, select

from lightly_studio.models.collection import CollectionTable, SampleType


def get_annotation_source_by_name(
    session: Session,
    dataset_collection_id: UUID,
    name: str,
) -> CollectionTable | None:
    """Retrieves the annotation source of a collection by its name.

    Args:
        session:
            The database session to use.
        dataset_collection_id:
            The UUID of the collection that owns the annotation source.
        name:
            The name of the annotation source.

    Returns:
        The annotation collection with this name, or None if the collection has no
        annotation source with this name.
    """
    statement = (
        select(CollectionTable)
        .where(col(CollectionTable.parent_collection_id) == dataset_collection_id)
        .where(CollectionTable.sample_type == SampleType.ANNOTATION)
        .where(CollectionTable.name == name)
    )
    return session.exec(statement).first()
