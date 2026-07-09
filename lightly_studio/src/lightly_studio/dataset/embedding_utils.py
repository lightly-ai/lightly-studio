"""Utility functions for embedding-related operations in Lightly Studio datasets."""

from uuid import UUID

from sqlmodel import Session, SQLModel

from lightly_studio.resolvers import (
    embedding_model_resolver,
    sample_embedding_resolver,
)


class CollectionEmbeddingsStatus(SQLModel):
    """Which embedding-based features are available for a collection."""

    has_embeddings: bool
    """At least one sample embedding is stored, under any embedding model.

    Enables the embedding plot, image similarity, and embedding-based sampling.
    """

    has_text_search_embeddings: bool
    """At least one sample embedding is stored under a text-capable embedding model.

    Enables text-based search. Custom embeddings (``Sample.set_embedding``) have no
    matching text encoder and do not count here.
    """


def get_collection_embeddings_status(
    session: Session, collection_id: UUID
) -> CollectionEmbeddingsStatus:
    """Report which embedding-based features are available for the given collection.

    Reads only the database (``embedding_model`` and ``sample_embedding`` tables); it
    never registers or loads embedding models as a side effect.

    Args:
        session: Database session for resolver operations.
        collection_id: The ID of the collection to check.

    Returns:
        The embeddings status of the collection.
    """
    embedding_models = embedding_model_resolver.get_all_by_collection_id(
        session=session, collection_id=collection_id
    )
    has_embeddings = sample_embedding_resolver.has_any_embedding(
        session=session,
        collection_id=collection_id,
        embedding_model_ids=[model.embedding_model_id for model in embedding_models],
    )
    if not has_embeddings:
        return CollectionEmbeddingsStatus(has_embeddings=False, has_text_search_embeddings=False)
    has_text_search_embeddings = sample_embedding_resolver.has_any_embedding(
        session=session,
        collection_id=collection_id,
        embedding_model_ids=[
            model.embedding_model_id for model in embedding_models if model.supports_text_search
        ],
    )
    return CollectionEmbeddingsStatus(
        has_embeddings=True, has_text_search_embeddings=has_text_search_embeddings
    )
