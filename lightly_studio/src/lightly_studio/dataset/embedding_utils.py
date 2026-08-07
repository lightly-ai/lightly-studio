"""Utility functions for embedding-related operations in Lightly Studio datasets."""

from uuid import UUID

from sqlmodel import Session

from lightly_studio.resolvers import (
    sample_embedding_resolver,
)


def collection_has_embeddings(session: Session, collection_id: UUID) -> bool:
    """Check if there are any embeddings available for the given collection.

    Model-free on purpose: resolving the collection's default model would register one,
    overwriting the record of what actually produced the stored vectors.

    Args:
        session: Database session for resolver operations.
        collection_id: The ID of the collection to check for embeddings.

    Returns:
        True if embeddings exist for the collection, False otherwise.
    """
    return sample_embedding_resolver.has_any_embeddings(
        session=session, collection_id=collection_id
    )
