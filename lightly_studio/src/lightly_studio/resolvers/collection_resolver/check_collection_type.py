"""Implementation of check_collection_type resolver function."""

from uuid import UUID

from sqlmodel import Session

from lightly_studio.models.collection import SampleType
from lightly_studio.resolvers import collection_resolver


def check_collection_type(session: Session, collection_id: UUID, expected_type: SampleType) -> None:
    """Check that the collection has the expected sample type.

    Raises a ValueError if the collection does not have the expected sample type or
    if it does not exist.

    Args:
        session: The database session.
        collection_id: The ID of the collection to check.
        expected_type: The expected sample type.
    """
    collection = collection_resolver.get_by_id(session=session, collection_id=collection_id)
    if collection is None:
        raise ValueError(f"Collection with id {collection_id} not found.")
    if collection.sample_type != expected_type:
        raise ValueError(
            f"Collection with id {collection_id} is having sample type "
            f"'{collection.sample_type.value}', expected '{expected_type.value}'."
        )
