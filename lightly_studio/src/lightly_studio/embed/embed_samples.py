"""Collection-level embedding and query orchestration."""

from __future__ import annotations

import logging
from uuid import UUID

from PIL.Image import Image
from sqlmodel import Session
from tqdm import tqdm

from lightly_studio.embed import default_embedder_resolver, embedding_storage
from lightly_studio.embed.embedder import (
    Capability,
    ImageCropPathEmbedder,
    ImagePathEmbedder,
    ImagePILEmbedder,
    TextEmbedder,
    VideoPathEmbedder,
)
from lightly_studio.embed.types import EmbeddingResult
from lightly_studio.models.collection import SampleType
from lightly_studio.resolvers import (
    annotation_resolver,
    collection_resolver,
    image_resolver,
    sample_resolver,
    video_resolver,
)
from lightly_studio.utils import batching

logger = logging.getLogger(__name__)
ANNOTATION_EMBED_BATCH_SIZE = 2048


def embed_image_for_collection(session: Session, collection_id: UUID, filepath: str) -> list[float]:
    """Embed one image with an existing collection default, without storing it."""
    embedder, _ = default_embedder_resolver.resolve(
        session=session, collection_id=collection_id, capability=Capability.IMAGE_PATH
    )
    if not isinstance(embedder, ImagePathEmbedder):
        raise ValueError("Image embedding is disabled for this collection.")
    result = embedder.embed_images(paths=[filepath])
    return _single_embedding(result.embeddings, result.kept_indices, "image")


def embed_text_for_collection(session: Session, collection_id: UUID, text: str) -> list[float]:
    """Embed one text query with an existing collection default, without storing it."""
    try:
        embedder, _ = default_embedder_resolver.resolve(
            session=session, collection_id=collection_id, capability=Capability.TEXT
        )
    except ValueError as exc:
        raise ValueError(f"Text search is disabled for this collection: {exc}") from exc
    if not isinstance(embedder, TextEmbedder):
        raise ValueError("Text search is disabled for this collection.")
    result = embedder.embed_text(texts=[text])
    return _single_embedding(result.embeddings, result.kept_indices, "text")


def embed_image_samples(session: Session, collection_id: UUID, sample_ids: list[UUID]) -> None:
    """Embed image samples and store the successfully generated rows."""
    _validate_collection(session=session, collection_id=collection_id, expected=SampleType.IMAGE)
    if not sample_ids:
        return
    resolved = _resolve_offline(
        session=session, collection_id=collection_id, capability=Capability.IMAGE_PATH
    )
    if resolved is None:
        return
    embedder, model_id = resolved
    if not isinstance(embedder, ImagePathEmbedder):
        return
    images = image_resolver.get_many_by_id(session=session, sample_ids=sample_ids)
    if len(images) != len(sample_ids):
        raise ValueError("Could not fetch all image paths for the provided IDs.")
    result = embedder.embed_images(paths=[image.file_path_abs for image in images])
    _store_result(session=session, model_id=model_id, sample_ids=sample_ids, result=result)


def embed_annotation_collection(session: Session, annotation_collection_id: UUID) -> None:
    """Embed unembedded annotation crops in chunks."""
    _validate_collection(
        session=session, collection_id=annotation_collection_id, expected=SampleType.ANNOTATION
    )
    resolved = _resolve_offline(
        session=session,
        collection_id=annotation_collection_id,
        capability=Capability.IMAGE_CROP_PATH,
    )
    if resolved is None:
        return
    if (
        sample_resolver.count_by_collection_id(
            session=session, collection_id=annotation_collection_id
        )
        == 0
    ):
        return
    embedder, model_id = resolved
    if not isinstance(embedder, ImageCropPathEmbedder):
        return
    sample_ids = annotation_resolver.get_unembedded_annotation_ids(
        session=session,
        annotation_collection_id=annotation_collection_id,
        embedding_model_id=model_id,
    )
    with tqdm(total=len(sample_ids), desc="Embedding annotations", unit=" crops") as progress:
        for chunk in batching.batched(items=sample_ids, batch_size=ANNOTATION_EMBED_BATCH_SIZE):
            crops = annotation_resolver.get_annotation_crops_for_ids(
                session=session, annotation_sample_ids=chunk
            )
            ids = [crop.annotation_sample_id for crop in crops]
            result = embedder.embed_image_crops(crops=[crop.image_crop for crop in crops])
            _store_result(
                session=session,
                model_id=model_id,
                sample_ids=ids,
                result=result,
                show_progress=False,
            )
            progress.update(len(crops))


def embed_video_samples(session: Session, collection_id: UUID, sample_ids: list[UUID]) -> None:
    """Embed video samples and store the successfully generated rows."""
    _validate_collection(session=session, collection_id=collection_id, expected=SampleType.VIDEO)
    if not sample_ids:
        return
    resolved = _resolve_offline(
        session=session, collection_id=collection_id, capability=Capability.VIDEO_PATH
    )
    if resolved is None:
        return
    embedder, model_id = resolved
    if not isinstance(embedder, VideoPathEmbedder):
        return
    videos = video_resolver.get_many_by_id(session=session, sample_ids=sample_ids)
    if len(videos) != len(sample_ids):
        raise ValueError("Could not fetch all video paths for the provided IDs.")
    result = embedder.embed_videos(paths=[video.file_path_abs for video in videos])
    _store_result(session=session, model_id=model_id, sample_ids=sample_ids, result=result)


def embed_frame_samples(
    session: Session, collection_id: UUID, sample_ids: list[UUID], pil_frames: list[Image]
) -> None:
    """Embed decoded video frames and store the successfully generated rows."""
    _validate_collection(
        session=session, collection_id=collection_id, expected=SampleType.VIDEO_FRAME
    )
    if not sample_ids and not pil_frames:
        return
    if len(sample_ids) != len(pil_frames):
        raise ValueError("Expected the same number of sample IDs and images.")
    resolved = _resolve_offline(
        session=session, collection_id=collection_id, capability=Capability.IMAGE_PIL
    )
    if resolved is None:
        return
    embedder, model_id = resolved
    if not isinstance(embedder, ImagePILEmbedder):
        return
    result = embedder.embed_images_pil(images=pil_frames)
    _store_result(
        session=session,
        model_id=model_id,
        sample_ids=sample_ids,
        result=result,
        show_progress=False,
    )


def collection_has_default_embedder(session: Session, collection_id: UUID) -> bool:
    """Ensure and report availability of an IMAGE_PIL collection default."""
    _validate_collection(
        session=session, collection_id=collection_id, expected=SampleType.VIDEO_FRAME
    )
    return (
        _resolve_offline(
            session=session, collection_id=collection_id, capability=Capability.IMAGE_PIL
        )
        is not None
    )


def _validate_collection(session: Session, collection_id: UUID, expected: SampleType) -> None:
    collection = collection_resolver.get_by_id(session=session, collection_id=collection_id)
    if collection is None:
        raise ValueError("Provided collection_id could not be found.")
    if collection.sample_type != expected:
        raise ValueError(
            f"Expected a {expected.value} collection, got {collection.sample_type.value}."
        )


def _resolve_offline(session: Session, collection_id: UUID, capability: Capability):
    try:
        embedder, model = default_embedder_resolver.resolve_or_bootstrap(
            session=session, collection_id=collection_id, capability=capability
        )
    except (ImportError, ValueError) as exc:
        logger.warning("No usable embedding model. Skipping embedding generation: %s", exc)
        return None
    return embedder, model.embedding_model_id


def _store_result(
    session: Session,
    model_id: UUID,
    sample_ids: list[UUID],
    result: EmbeddingResult,
    show_progress: bool = True,
) -> None:
    if any(index < 0 or index >= len(sample_ids) for index in result.kept_indices):
        raise ValueError("Embedder returned a kept index outside the input range.")
    kept_sample_ids = [sample_ids[index] for index in result.kept_indices]
    embedding_storage.store_embeddings(
        session=session,
        model_id=model_id,
        sample_ids=kept_sample_ids,
        embeddings=result.embeddings,
        show_progress=show_progress,
    )


def _single_embedding(embeddings, kept_indices: list[int], input_name: str) -> list[float]:
    if kept_indices != [0] or len(embeddings) != 1:
        raise ValueError(f"The {input_name} input could not be embedded.")
    return embeddings[0].tolist()
