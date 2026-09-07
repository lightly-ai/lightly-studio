"""Utility functions for embedding-related operations in Lightly Studio datasets."""

from uuid import UUID

from sqlmodel import Session

from lightly_studio.resolvers import (
    collection_embedding_model_resolver,
    sample_embedding_resolver,
)


def collection_has_embeddings(session: Session, collection_id: UUID) -> bool:
    """Check if there are any embeddings available for the given collection.

    Resolves the collection's default embedding model from the database and reports whether
    any embeddings are stored for it. Does not load the model.

    Args:
        session: Database session for resolver operations.
        collection_id: The ID of the collection to check for embeddings.

    Returns:
        True if embeddings exist for the collection, False otherwise.
    """
    model_id = collection_embedding_model_resolver.get_default_by_collection_id(
        session=session,
        collection_id=collection_id,
    )
    if model_id is None:
        # No default embedding model registered for this collection.
        return False

    return (
        sample_embedding_resolver.get_embedding_count(
            session=session, collection_id=collection_id, embedding_model_id=model_id
        )
        > 0
    )
