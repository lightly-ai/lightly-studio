"""Class-free interface for embedding samples and queries.

Wraps the shared embedding logic behind plain module functions so callers resolve the
collection's default embedding model themselves. Each function resolves its embedder from
the capability-typed ``EmbedderRegistry``.
"""

from __future__ import annotations

import io
import logging
import tempfile
from pathlib import Path
from uuid import UUID

from lightly_studio_serve.embedder import (
    Embedder,
    ImageBytesEmbedder,
    ImageCropPathEmbedder,
    ImagePathEmbedder,
    ImagePILEmbedder,
)
from lightly_studio_serve.types import EmbeddingResult
from PIL import Image as PILImage
from PIL.Image import Image
from sqlmodel import Session
from tqdm import tqdm

from lightly_studio.core.file_outcome_report import BROKEN_IMAGE_ERRORS
from lightly_studio.embed import default_embedder, embedding_storage
from lightly_studio.embed.embedder_config import EmbedderConfig
from lightly_studio.embed.embedder_registry import EmbedderRegistry
from lightly_studio.resolvers import (
    annotation_resolver,
    image_resolver,
    video_resolver,
)
from lightly_studio.utils import batching

logger = logging.getLogger(__name__)

# Crops are embedded in chunks so an image's annotations tend to land in the same chunk,
# keeping a single open per image.
_ANNOTATION_EMBED_BATCH_SIZE = 2048


class ImageNotEmbeddedError(ValueError):
    """Raised when the embedder returns no embedding for an image to embed.

    A broken or unsupported image is the reason an embedder drops an input, so a caller
    may report this as a bad request. Subclasses ``ValueError`` so a caller that handles
    the other input errors of this module keeps working.
    """


def embed_image_for_collection(
    session: Session, collection_id: UUID, image_bytes: bytes
) -> list[float]:
    """Embed a single uploaded image with the collection's default model, without storing it.

    Resolves the collection's default model from the database and embeds the image with the
    registry's embedder for that model's space. Unlike the ``embed_*_samples`` functions this
    never bootstraps a default model, since an interactive query must not mutate the collection.
    Takes bytes rather than a path so a remote backend without filesystem access can serve it.
    A space whose embedder embeds images by PIL image or by path only gets the decoded image
    or a temporary file, so image search stays available for every embedder that embeds images.

    Args:
        session: Database session for resolver operations.
        collection_id: The collection whose default embedding model is used.
        image_bytes: Encoded image bytes (JPEG, PNG or WebP).

    Returns:
        The embedding as a list of floats.

    Raises:
        ImageNotEmbeddedError: If the image bytes do not decode, or the embedder returns no
            embedding for them.
        ValueError: If the collection has no default embedding model, or no registered
            embedder matches that model's space.
    """
    embedder = default_embedder.resolve_query_embedder(
        session=session,
        collection_id=collection_id,
        get_embedder_fn=_get_query_image_embedder,
    )
    result = _embed_image_bytes(embedder=embedder, image_bytes=image_bytes)
    if result.kept_indices != [0]:
        raise ImageNotEmbeddedError(
            "The embedder returned no embedding for the uploaded image. The image may be "
            "broken or in a format the embedder does not support."
        )
    embedding: list[float] = result.embeddings[0].tolist()
    return embedding


def embed_text_for_collection(session: Session, collection_id: UUID, text: str) -> list[float]:
    """Embed a text query with the collection's default model, without storing it.

    Resolves the collection's default model from the database and embeds the text with the
    registry's embedder for that model's space. Unlike the ``embed_*_samples`` functions this
    never bootstraps a default model, since an interactive query must not mutate the collection.

    Args:
        session: Database session for resolver operations.
        collection_id: The collection whose default embedding model is used.
        text: The text to embed.

    Returns:
        The embedding as a list of floats.

    Raises:
        ValueError: If the collection has no default embedding model, no registered
            embedder matches that model's space, or the embedder produced no embedding
            for the text.
    """
    embedder = default_embedder.resolve_query_embedder(
        session=session,
        collection_id=collection_id,
        get_embedder_fn=EmbedderRegistry.get_text_embedder,
    )
    result = embedder.embed_text(texts=[text])
    if result.kept_indices != [0]:
        raise ValueError(f"The embedder produced no embedding for text {text!r}.")
    embedding: list[float] = result.embeddings[0].tolist()
    return embedding


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


def embed_annotation_collection(session: Session, annotation_collection_id: UUID) -> None:
    """Embed the crops of an annotation collection and store the result.

    When the collection has a default embedding model, its space selects the embedder.
    Otherwise the registry's default crop embedder is used and registered as the
    collection's default. Does nothing (and logs a warning) if no crop embedder is
    available.

    Args:
        session: Database session for resolver operations.
        annotation_collection_id: The annotation collection whose crops are embedded.
    """
    default_embedder_and_model_id = default_embedder.resolve_default_embedder(
        session=session,
        collection_id=annotation_collection_id,
        get_embedder_fn=EmbedderRegistry.get_image_crop_path_embedder,
    )
    if default_embedder_and_model_id is None:
        return
    embedder, model_id = default_embedder_and_model_id

    annotation_sample_ids = annotation_resolver.get_unembedded_annotation_ids(
        session=session,
        annotation_collection_id=annotation_collection_id,
        embedding_model_id=model_id,
    )
    if not annotation_sample_ids:
        logger.info("No annotation crops to embed.")
        return

    with tqdm(
        total=len(annotation_sample_ids), desc="Embedding annotations", unit=" crops"
    ) as progress:
        for sample_id_chunk in batching.batched(
            items=annotation_sample_ids, batch_size=_ANNOTATION_EMBED_BATCH_SIZE
        ):
            embedded_count = _embed_annotation_chunk(
                session=session,
                embedder=embedder,
                model_id=model_id,
                annotation_sample_ids=sample_id_chunk,
            )
            progress.update(embedded_count)


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
    if len(sample_ids) != len(pil_frames):
        raise ValueError(
            f"Number of sample IDs ({len(sample_ids)}) does not match number of frames "
            f"({len(pil_frames)})."
        )

    if not sample_ids:
        logger.warning("No frame samples to embed. Skipping embedding generation.")
        return

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

    # Frames are embedded one video-batch at a time during ingest, so the progress bar
    # is disabled to keep noninteractive output clean.
    embedding_storage.store_embeddings(
        session=session,
        model_id=model_id,
        sample_ids=kept_sample_ids,
        embeddings=result.embeddings,
        show_progress=False,
    )


def has_frame_embedder(session: Session, collection_id: UUID) -> bool:
    """Report whether an embedder is available for a collection's video frames.

    Resolves the embedder the same way as ``embed_frame_samples``, so frame decoding is
    skipped exactly when ``embed_frame_samples`` would find no embedder for the collection's
    space and store nothing.

    Args:
        session: Database session for resolver operations.
        collection_id: The video-frame collection whose default model selects the space.
    """
    # TODO(Michal, 09/2026): This loads the built-in embedder and registers a default model,
    # which is wasted when the caller embeds no frames, for example when every video is
    # already present. A cheaper check would report availability without loading the model.
    return (
        default_embedder.resolve_default_embedder(
            session=session,
            collection_id=collection_id,
            get_embedder_fn=EmbedderRegistry.get_image_pil_embedder,
        )
        is not None
    )


def _get_query_image_embedder(
    registry: EmbedderRegistry, space_key: str | None, config: EmbedderConfig | None
) -> ImageBytesEmbedder | ImagePILEmbedder | ImagePathEmbedder | None:
    """Get the space's image embedder, preferring bytes, then PIL images, then paths.

    Args:
        registry: The registry the embedder is resolved from.
        space_key: The embedding space to resolve, or None for the registry default.
        config: The stored configuration of the space, used only when no embedder is
            registered for it.

    Returns:
        The space's image embedder, or None if the space embeds no images.
    """
    return (
        registry.get_image_bytes_embedder(space_key=space_key, config=config)
        or registry.get_image_pil_embedder(space_key=space_key, config=config)
        or registry.get_image_path_embedder(space_key=space_key, config=config)
    )


def _embed_image_bytes(embedder: Embedder, image_bytes: bytes) -> EmbeddingResult:
    """Embed one encoded image with the capability the embedder has.

    An embedder without the bytes capability gets the decoded image, or the bytes written
    to a temporary file that is removed after the call.

    Args:
        embedder: The image embedder of the space, as ``_get_query_image_embedder``
            returns it.
        image_bytes: Encoded image bytes (JPEG, PNG or WebP).

    Returns:
        The embedding result for the single image.

    Raises:
        ImageNotEmbeddedError: If the embedder needs a decoded image or a file and the
            bytes do not decode.
    """
    if isinstance(embedder, ImageBytesEmbedder):
        return embedder.embed_image_bytes(images=[image_bytes])

    try:
        image = PILImage.open(io.BytesIO(image_bytes))
        image.load()
    except BROKEN_IMAGE_ERRORS as error:
        raise ImageNotEmbeddedError("The uploaded image cannot be decoded.") from error

    if isinstance(embedder, ImagePILEmbedder):
        return embedder.embed_images_pil(images=[image.convert("RGB")])

    assert isinstance(embedder, ImagePathEmbedder)
    # The suffix comes from the decoded format, as the upload's file name is not known here.
    suffix = "" if image.format is None else f".{image.format.lower()}"
    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / f"image{suffix}"
        path.write_bytes(image_bytes)
        return embedder.embed_images(paths=[str(path)])


def _embed_annotation_chunk(
    session: Session,
    embedder: ImageCropPathEmbedder,
    model_id: UUID,
    annotation_sample_ids: list[UUID],
) -> int:
    """Resolve, embed and store one chunk of annotation crops.

    Crops the embedder drops (see ``kept_indices``) are left out, so the stored sample
    ids stay aligned with the returned embeddings.

    Args:
        session: Database session for resolver operations.
        embedder: The crop embedder resolved for the collection.
        model_id: The model id the embeddings are stored under.
        annotation_sample_ids: The annotation ids in this chunk.

    Returns:
        The number of crops resolved from the chunk, for progress reporting.
    """
    annotation_crops = annotation_resolver.get_annotation_crops_for_ids(
        session=session, annotation_sample_ids=annotation_sample_ids
    )
    if not annotation_crops:
        return 0

    result = embedder.embed_image_crops(crops=[crop.image_crop for crop in annotation_crops])
    crop_sample_ids = [crop.annotation_sample_id for crop in annotation_crops]
    kept_sample_ids = [crop_sample_ids[index] for index in result.kept_indices]
    # The collection-level bar in embed_annotation_collection tracks progress, so the
    # per-chunk storage bar is disabled to avoid a redundant bar for every chunk.
    embedding_storage.store_embeddings(
        session=session,
        model_id=model_id,
        sample_ids=kept_sample_ids,
        embeddings=result.embeddings,
        show_progress=False,
    )
    return len(annotation_crops)
