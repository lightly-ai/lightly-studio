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

from PIL.Image import Image
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


def embed_video_samples(session: Session, collection_id: UUID, sample_ids: list[UUID]) -> None:
    """Embed video samples with the collection's default model and store the result.

    Does nothing (and logs a warning) if the collection has no usable default model.

    Args:
        session: Database session for resolver operations.
        collection_id: The collection whose default embedding model is used.
        sample_ids: Video sample IDs to embed.
    """
    manager = EmbeddingManagerProvider.get_embedding_manager()
    model_id = manager.load_or_get_default_model(session=session, collection_id=collection_id)
    if model_id is None:
        logger.warning("No embedding model loaded. Skipping embedding generation.")
        return

    manager.embed_videos(
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


def embed_frame_samples(
    session: Session,
    collection_id: UUID,
    sample_ids: list[UUID],
    pil_frames: list[Image],
) -> None:
    """Embed the frames of a single video and store the result.

    Uses the frame collection's default model. Does nothing (and logs a warning) if it
    has no usable default model.

    Args:
        session: Database session for resolver operations.
        collection_id: The video-frame collection whose default embedding model is used.
        sample_ids: Frame sample IDs the embeddings are stored for.
        pil_frames: The frames to embed, in the same order as ``sample_ids``.
    """
    manager = EmbeddingManagerProvider.get_embedding_manager()
    model_id = manager.load_or_get_default_model(session=session, collection_id=collection_id)
    if model_id is None:
        logger.warning("No embedding model loaded. Skipping embedding generation.")
        return

    manager.embed_and_store_pil_images(
        session=session,
        embedding_model_id=model_id,
        sample_ids=sample_ids,
        images=pil_frames,
        show_progress=False,
    )


def collection_has_default_embedder(session: Session, collection_id: UUID) -> bool:
    """Ensure the collection's default embedding model is loaded and report whether it exists.

    This is an ensure-and-check, not a pure peek: on the first call for a collection,
    ``load_or_get_default_model`` loads and registers the collection's default embedding
    model as a side effect, then this returns whether a usable default model is (now)
    available.

    This differs from ``embedding_utils.collection_has_embeddings``, which checks whether
    embeddings are already *stored* for the collection.

    Args:
        session: Database session for resolver operations.
        collection_id: The collection whose default embedding model is ensured.

    Returns:
        True if the collection has a usable default embedding model, False otherwise.
    """
    manager = EmbeddingManagerProvider.get_embedding_manager()
    model_id = manager.load_or_get_default_model(session=session, collection_id=collection_id)
    return model_id is not None
