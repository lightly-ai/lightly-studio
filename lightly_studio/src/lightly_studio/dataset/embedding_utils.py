"""Utility functions for embedding-related operations in Lightly Studio datasets."""

from uuid import UUID

from sqlmodel import Session

from lightly_studio.resolvers import (
    embedding_model_resolver,
    sample_embedding_resolver,
)


def collection_has_embeddings(session: Session, collection_id: UUID) -> bool:
    """Check if there are any embeddings available for the given collection.

    This is a pure database check so it works regardless of which embedding
    manager produced the vectors. The new ``EmbedderManager`` ingest path creates
    the ``embedding_model`` and ``sample_embedding`` rows directly, without
    registering anything in the old ``EmbeddingManager``, so gating on the old
    manager would hide embeddings that actually exist.

    Args:
        session: Database session for resolver operations.
        collection_id: The ID of the collection to check for embeddings.

    Returns:
        True if embeddings exist for the collection, False otherwise.
    """
    embedding_models = embedding_model_resolver.get_all_by_collection_id(
        session=session, collection_id=collection_id
    )
    return any(
        sample_embedding_resolver.get_embedding_count(
            session=session,
            collection_id=collection_id,
            embedding_model_id=embedding_model.embedding_model_id,
        )
        > 0
        for embedding_model in embedding_models
    )
