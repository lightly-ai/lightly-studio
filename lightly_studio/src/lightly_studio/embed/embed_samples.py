"""Class-free interface for embedding samples and queries.

Wraps the shared embedding logic behind plain module functions so callers no longer
reach for the ``EmbeddingManager`` singleton, resolve the default model, and check it
by hand. Each function resolves the collection's default embedding model itself.

The functions currently delegate to the ``EmbeddingManager`` singleton. The internals
will be swapped for the capability-typed ``EmbedderRegistry`` later; the function
signatures are the stable surface callers migrate to now.
"""

from __future__ import annotations

import logging
from uuid import UUID

from sqlmodel import Session

from lightly_studio.dataset.embedding_manager import (
    EmbeddingManagerProvider,
    TextEmbedQuery,
)

logger = logging.getLogger(__name__)


def embed_image_for_collection(collection_id: UUID, filepath: str) -> list[float]:
    """Embed a single image with the collection's default model, without storing it.

    Args:
        collection_id: The collection whose default embedding model is used.
        filepath: fsspec path or URL of the image to embed.

    Returns:
        The embedding as a list of floats.

    Raises:
        ValueError: If the collection has no default embedding model, or the model does
            not support images.
    """
    manager = EmbeddingManagerProvider.get_embedding_manager()
    return manager.compute_image_embedding(collection_id=collection_id, filepath=filepath)


def embed_text_for_collection(collection_id: UUID, text: str) -> list[float]:
    """Embed a text query with the collection's default model, without storing it.

    Args:
        collection_id: The collection whose default embedding model is used.
        text: The text to embed.

    Returns:
        The embedding as a list of floats.

    Raises:
        ValueError: If the collection has no default embedding model.
    """
    manager = EmbeddingManagerProvider.get_embedding_manager()
    return manager.embed_text(collection_id=collection_id, text_query=TextEmbedQuery(text=text))


def embed_image_samples(session: Session, collection_id: UUID, sample_ids: list[UUID]) -> None:
    """Embed image samples with the collection's default model and store the result.

    Does nothing (and logs a warning) if the collection has no usable default model.

    Args:
        session: Database session for resolver operations.
        collection_id: The collection whose default embedding model is used.
        sample_ids: Image sample IDs to embed.
    """
    manager = EmbeddingManagerProvider.get_embedding_manager()
    model_id = manager.load_or_get_default_model(session=session, collection_id=collection_id)
    if model_id is None:
        logger.warning("No embedding model loaded. Skipping embedding generation.")
        return

    manager.embed_images(
        session=session,
        collection_id=collection_id,
        sample_ids=sample_ids,
        embedding_model_id=model_id,
    )


def embed_annotation_collection(session: Session, annotation_collection_id: UUID) -> None:
    """Embed the crops of an annotation collection and store the result.

    Uses the annotation collection's default model. Does nothing (and logs a warning) if
    it has no usable default model.

    Args:
        session: Database session for resolver operations.
        annotation_collection_id: The annotation collection whose crops are embedded.
    """
    manager = EmbeddingManagerProvider.get_embedding_manager()
    model_id = manager.load_or_get_default_model(
        session=session, collection_id=annotation_collection_id
    )
    if model_id is None:
        logger.warning("No embedding model loaded. Skipping embedding generation.")
        return

    manager.embed_annotations(
        session=session,
        annotation_collection_id=annotation_collection_id,
        embedding_model_id=model_id,
    )
