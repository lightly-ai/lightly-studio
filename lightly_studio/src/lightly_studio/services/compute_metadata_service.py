"""Compute metadata from the embeddings of an embedding model that is given by name."""

from __future__ import annotations

from uuid import UUID

from sqlmodel import Session

from lightly_studio.metadata import compute_similarity, compute_typicality
from lightly_studio.resolvers import collection_embedding_model_resolver


def compute_typicality_metadata(
    session: Session, collection_id: UUID, embedding_model_name: str | None, metadata_name: str
) -> None:
    """Compute the typicality of each sample and store it as metadata.

    Args:
        session: The database session.
        collection_id: The ID of the collection.
        embedding_model_name: The embedding model. None uses the default model.
        metadata_name: The metadata key for the values.

    Raises:
        ValueError: If the embedding model does not exist.
    """
    embedding_model_id = collection_embedding_model_resolver.get_model_id_by_name(
        session=session, collection_id=collection_id, embedding_model_name=embedding_model_name
    )
    compute_typicality.compute_typicality_metadata(
        session=session,
        collection_id=collection_id,
        embedding_model_id=embedding_model_id,
        metadata_name=metadata_name,
    )


def compute_similarity_metadata(
    session: Session,
    collection_id: UUID,
    query_tag_id: UUID,
    embedding_model_name: str | None,
    metadata_name: str | None,
) -> str:
    """Compute the similarity of each sample to the tagged samples and store it as metadata.

    Args:
        session: The database session.
        collection_id: The ID of the collection.
        query_tag_id: The ID of the tag of the query samples.
        embedding_model_name: The embedding model. None uses the default model.
        metadata_name: The metadata key for the values. None makes a new key.

    Returns:
        The metadata key for the values.

    Raises:
        EmbeddingModelNotFoundError: If the embedding model does not exist.
        TagNotFoundError: If the query tag does not exist.
    """
    embedding_model_id = collection_embedding_model_resolver.get_model_id_by_name(
        session=session, collection_id=collection_id, embedding_model_name=embedding_model_name
    )
    return compute_similarity.compute_similarity_metadata(
        session=session,
        key_collection_id=collection_id,
        embedding_model_id=embedding_model_id,
        query_tag_id=query_tag_id,
        metadata_name=metadata_name,
    )
