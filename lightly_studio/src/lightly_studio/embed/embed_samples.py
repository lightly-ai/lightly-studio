"""Class-free interface for embedding samples and queries.

Wraps the shared embedding logic behind plain module functions so callers no longer
reach for the ``EmbeddingManager`` singleton, resolve the default model, and check it
by hand. Each function resolves the collection's default embedding model itself.

The functions currently delegate to the ``EmbeddingManager`` singleton. The internals
will be swapped for the capability-typed ``EmbedderRegistry`` later; the function
signatures are the stable surface callers migrate to now.
"""

from __future__ import annotations

from uuid import UUID

from lightly_studio.dataset.embedding_manager import (
    EmbeddingManagerProvider,
    TextEmbedQuery,
)


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
