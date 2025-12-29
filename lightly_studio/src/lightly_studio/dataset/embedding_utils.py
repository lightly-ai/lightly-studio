"""Utility functions for embedding-related operations in Lightly Studio datasets."""

from uuid import UUID

from sqlmodel import Session

from lightly_studio.dataset.embedding_manager import EmbeddingManagerProvider
from lightly_studio.resolvers import (
    sample_embedding_resolver,
)


def collection_has_embeddings(session: Session, collection_id: UUID) -> bool:
    """Check if there are any embeddings available for the given collection.

    Args:
        session: Database session for resolver operations.
        collection_id: The ID of the collection to check for embeddings.

    Returns:
        True if embeddings exist for the collection, False otherwise.
    """
    embedding_manager = EmbeddingManagerProvider.get_embedding_manager()
    model_id = embedding_manager.load_or_get_default_model(
        session=session,
        collection_id=collection_id,
    )
    if model_id is None:
        # No default embedding model loaded for this collection.
        return False

    return (
        sample_embedding_resolver.get_embedding_count(
            session=session, collection_id=collection_id, embedding_model_id=model_id
        )
        > 0
    )
