"""Class-free interface for embedding samples and queries.

Wraps the shared embedding logic behind plain module functions so callers no longer
reach for the ``EmbeddingManager`` singleton, resolve the default model, and check it
by hand. Each function resolves the collection's default embedding model itself.

The functions currently delegate to the ``EmbeddingManager`` singleton. The internals
are being swapped for the capability-typed ``EmbedderRegistry``; ``embed_image_samples``,
``embed_video_samples`` and ``embed_frame_samples`` already use it. The function signatures
are the stable surface callers migrate to now.
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
from lightly_studio.embed import default_embedder, embedding_storage
from lightly_studio.embed.embedder_registry import EmbedderRegistry
from lightly_studio.resolvers import image_resolver, video_resolver

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

    When the collection has a default embedding model, its space selects the embedder.
    Otherwise the registry's default image embedder is used and registered as the
    collection's default. Does nothing (and logs a warning) if no image embedder is
    available.

    Args:
        session: Database session for resolver operations.
        collection_id: The collection whose default embedding model is used.
        sample_ids: Image sample IDs to embed.
    """
    if not sample_ids:
        logger.warning("No image samples to embed. Skipping embedding generation.")
        return

    # Resolve and validate paths before selecting a default embedder, which mutates the
    # collection's default model. A failed lookup must not leave a default model behind.
    sample_id_to_filepath = {
        sample.sample_id: sample.file_path_abs
        for sample in image_resolver.get_many_by_id(session=session, sample_ids=sample_ids)
    }
    if len(sample_id_to_filepath) != len(sample_ids):
        raise ValueError("Could not fetch all image paths for the provided IDs.")
    filepaths = [sample_id_to_filepath[sample_id] for sample_id in sample_ids]

    default_embedder_and_model_id = default_embedder.resolve_default_embedder(
        session=session,
        collection_id=collection_id,
        get_embedder_fn=EmbedderRegistry.get_image_path_embedder,
    )
    if default_embedder_and_model_id is None:
        return
    embedder, model_id = default_embedder_and_model_id

    result = embedder.embed_images(paths=filepaths)
    kept_sample_ids = [sample_ids[index] for index in result.kept_indices]

    embedding_storage.store_embeddings(
        session=session,
        model_id=model_id,
        sample_ids=kept_sample_ids,
        embeddings=result.embeddings,
    )

    _register_legacy_default_model(session=session, collection_id=collection_id, model_id=model_id)


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


def embed_video_samples(session: Session, collection_id: UUID, sample_ids: list[UUID]) -> None:
    """Embed video samples with the collection's default model and store the result.

    When the collection has a default embedding model, its space selects the embedder.
    Otherwise the registry's default video embedder is used and registered as the
    collection's default. Does nothing (and logs a warning) if no video embedder is
    available.

    Args:
        session: Database session for resolver operations.
        collection_id: The collection whose default embedding model is used.
        sample_ids: Video sample IDs to embed.
    """
    if not sample_ids:
        logger.warning("No video samples to embed. Skipping embedding generation.")
        return

    # Resolve and validate paths before selecting a default embedder, which mutates the
    # collection's default model. A failed lookup must not leave a default model behind.
    # The resolver returns videos in the input order. A length mismatch means an id has no video.
    videos = video_resolver.get_many_by_id(session=session, sample_ids=sample_ids)
    if len(videos) != len(sample_ids):
        raise ValueError("Could not fetch all video paths for the provided IDs.")
    filepaths = [video.file_path_abs for video in videos]

    default_embedder_and_model_id = default_embedder.resolve_default_embedder(
        session=session,
        collection_id=collection_id,
        get_embedder_fn=EmbedderRegistry.get_video_path_embedder,
    )
    if default_embedder_and_model_id is None:
        return
    embedder, model_id = default_embedder_and_model_id

    result = embedder.embed_videos(paths=filepaths)
    kept_sample_ids = [sample_ids[index] for index in result.kept_indices]

    embedding_storage.store_embeddings(
        session=session,
        model_id=model_id,
        sample_ids=kept_sample_ids,
        embeddings=result.embeddings,
    )

    _register_legacy_default_model(session=session, collection_id=collection_id, model_id=model_id)


def embed_frame_samples(
    session: Session,
    collection_id: UUID,
    sample_ids: list[UUID],
    pil_frames: list[Image],
) -> None:
    """Embed the frames of a single video and store the result.

    When the collection has a default embedding model, its space selects the embedder.
    Otherwise the registry's default PIL embedder is used and registered as the
    collection's default. Does nothing (and logs a warning) if no PIL embedder is
    available.

    Args:
        session: Database session for resolver operations.
        collection_id: The video-frame collection whose default embedding model is used.
        sample_ids: Frame sample IDs the embeddings are stored for.
        pil_frames: The frames to embed, in the same order as ``sample_ids``.
    """
    if not sample_ids:
        logger.warning("No frame samples to embed. Skipping embedding generation.")
        return

    if len(sample_ids) != len(pil_frames):
        raise ValueError(
            f"Number of sample IDs ({len(sample_ids)}) does not match number of frames "
            f"({len(pil_frames)})."
        )

    default_embedder_and_model_id = default_embedder.resolve_default_embedder(
        session=session,
        collection_id=collection_id,
        get_embedder_fn=EmbedderRegistry.get_image_pil_embedder,
    )
    if default_embedder_and_model_id is None:
        return
    embedder, model_id = default_embedder_and_model_id

    result = embedder.embed_images_pil(images=pil_frames)
    kept_sample_ids = [sample_ids[index] for index in result.kept_indices]

    embedding_storage.store_embeddings(
        session=session,
        model_id=model_id,
        sample_ids=kept_sample_ids,
        embeddings=result.embeddings,
    )

    _register_legacy_default_model(session=session, collection_id=collection_id, model_id=model_id)


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


# TODO(Michal, 09/2026): Remove once text and image search read embedders from the
# EmbedderRegistry instead of the EmbeddingManager. The query functions
# (embed_text_for_collection, embed_image_for_collection) still resolve their generator
# from the manager's in-memory maps, which the registry path does not populate.
def _register_legacy_default_model(session: Session, collection_id: UUID, model_id: UUID) -> None:
    """Sync the collection's default model into the legacy EmbeddingManager.

    Loads the manager's own generator for the collection and raises if it resolves to a
    different model than the registry stored, which means search would use a stale model.

    Args:
        session: Database session for resolver operations.
        collection_id: The collection whose default model is synced.
        model_id: The model id the registry stored embeddings under.

    Raises:
        ValueError: If the manager's default model differs from the registry's.
    """
    manager = EmbeddingManagerProvider.get_embedding_manager()
    legacy_model_id = manager.load_or_get_default_model(
        session=session, collection_id=collection_id
    )
    if legacy_model_id != model_id:
        raise ValueError(
            f"The legacy EmbeddingManager resolved a different default model "
            f"({legacy_model_id}) than the registry stored ({model_id})."
        )
