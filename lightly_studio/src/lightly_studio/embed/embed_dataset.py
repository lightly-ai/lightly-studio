"""Dataset-level embedding: embeds the samples of a collection that lack an embedding."""

from __future__ import annotations

import logging
from uuid import UUID

from lightly_studio_serve.embedder import ImageCropPathEmbedder, ImagePathEmbedder
from sqlmodel import Session
from tqdm import tqdm

from lightly_studio.core.file_outcome_report import AllInputFilesFailedError
from lightly_studio.embed import default_embedder, embedding_storage
from lightly_studio.embed.errors import NoUsableEmbedderError
from lightly_studio.resolvers import (
    annotation_resolver,
    collection_embedding_model_resolver,
    collection_resolver,
    image_resolver,
)
from lightly_studio.utils import batching

logger = logging.getLogger(__name__)

# Embed and commit images in chunks, so that an embedder failure keeps the earlier chunks
_IMAGE_EMBED_BATCH_SIZE = 1024

# Crops are embedded in chunks so an image's annotations tend to land in the same chunk,
# keeping a single open per image.
_ANNOTATION_EMBED_BATCH_SIZE = 2048


def compute_embeddings(
    session: Session,
    collection_id: UUID,
    embed_annotations: bool,
    recompute_annotations: bool,
) -> None:
    """Embeds the images without an embedding, then the annotation crops.

    A chunk where every file failed is logged and skipped.

    Args:
        session: Database session for resolver operations.
        collection_id: The image collection to embed.
        embed_annotations: If True, the crops of every annotation source are embedded too.
        recompute_annotations: If True, every croppable annotation is re-embedded.
            Otherwise only annotations without an embedding are embedded.

    Raises:
        NoUsableEmbedderError: If samples need an embedding and no embedder is available.
    """
    image_count = embed_missing_images(
        session=session, collection_id=collection_id, skip_failed_chunks=True
    )
    if image_count is None:
        raise NoUsableEmbedderError("No image embedder is available to embed the images.")

    annotation_count = 0
    if embed_annotations:
        for annotation_source in collection_resolver.get_annotation_collections(
            session=session, parent_collection_id=collection_id
        ):
            stored = embed_annotation_crops(
                session=session,
                annotation_collection_id=annotation_source.collection_id,
                recompute=recompute_annotations,
                skip_failed_chunks=True,
            )
            if stored is None:
                raise NoUsableEmbedderError(
                    "No crop embedder is available to embed the annotations of the "
                    f"annotation source {annotation_source.name!r}."
                )
            annotation_count += stored
    logger.info("Embedded %d images and %d annotations.", image_count, annotation_count)


def embed_missing_images(
    session: Session, collection_id: UUID, skip_failed_chunks: bool = False
) -> int | None:
    """Embeds every image of the collection without an embedding of the default model.

    The selection runs before the embedder is resolved. Resolving registers a default
    model when the collection has none, so a collection without images to embed is left
    untouched.

    Args:
        session: Database session for resolver operations.
        collection_id: The collection whose images are embedded.
        skip_failed_chunks: If True, a chunk where every file failed is logged and skipped.
            Otherwise the ``AllInputFilesFailedError`` propagates.

    Returns:
        The number of stored embeddings, or None if the selection is not empty and no
        image embedder is available.
    """
    default_model_id = collection_embedding_model_resolver.get_default_by_collection_id(
        session=session, collection_id=collection_id
    )
    sample_ids = image_resolver.get_unembedded_sample_ids(
        session=session, collection_id=collection_id, embedding_model_id=default_model_id
    )
    if not sample_ids:
        return 0

    resolved = default_embedder.resolve_default_embedder(
        session=session,
        collection_id=collection_id,
        embedder_type=ImagePathEmbedder,
    )
    if resolved is None:
        return None
    embedder, model_id = resolved

    stored = 0
    with tqdm(total=len(sample_ids), desc="Embedding images", unit=" images") as progress:
        for sample_id_chunk in batching.batched(
            items=sample_ids, batch_size=_IMAGE_EMBED_BATCH_SIZE
        ):
            try:
                stored += _embed_image_chunk(
                    session=session,
                    embedder=embedder,
                    model_id=model_id,
                    sample_ids=sample_id_chunk,
                )
            except AllInputFilesFailedError:
                if not skip_failed_chunks:
                    raise
                logger.warning(
                    "Skipping a chunk of %d images where every file failed.", len(sample_id_chunk)
                )
            progress.update(len(sample_id_chunk))
    return stored


def embed_annotation_crops(
    session: Session,
    annotation_collection_id: UUID,
    recompute: bool = False,
    skip_failed_chunks: bool = False,
) -> int | None:
    """Embeds the crops of an annotation source that lack an embedding, or all with recompute.

    The selection runs before the embedder is resolved. Resolving registers a default
    model when the collection has none, so an annotation source without croppable
    annotations (for example classifications only) is left untouched.

    When the collection has a default embedding model, its space selects the embedder.
    Otherwise the space of the parent collection is used, unless a registration set
    the crop bootstrap or the parent has no default. Then the registry's default crop
    embedder is used. See ``resolve_default_embedder``.

    Crops are written with an upsert, so a recomputed crop replaces its earlier vector.
    A crop the embedder drops keeps its earlier vector.

    Args:
        session: Database session for resolver operations.
        annotation_collection_id: The annotation collection whose crops are embedded.
        recompute: If True, embeds every croppable annotation, replacing stored embeddings.
        skip_failed_chunks: If True, a chunk where every file failed is logged and skipped.
            Otherwise the ``AllInputFilesFailedError`` propagates.

    Returns:
        The number of stored embeddings, or None if the selection is not empty and no
        crop embedder is available.
    """
    default_model_id = collection_embedding_model_resolver.get_default_by_collection_id(
        session=session, collection_id=annotation_collection_id
    )
    if recompute:
        annotation_sample_ids = annotation_resolver.get_croppable_annotation_ids(
            session=session, annotation_collection_id=annotation_collection_id
        )
    else:
        annotation_sample_ids = annotation_resolver.get_unembedded_annotation_ids(
            session=session,
            annotation_collection_id=annotation_collection_id,
            embedding_model_id=default_model_id,
        )
    if not annotation_sample_ids:
        return 0

    resolved = default_embedder.resolve_default_embedder(
        session=session,
        collection_id=annotation_collection_id,
        embedder_type=ImageCropPathEmbedder,
    )
    if resolved is None:
        return None
    embedder, model_id = resolved

    stored = 0
    with tqdm(
        total=len(annotation_sample_ids), desc="Embedding annotations", unit=" crops"
    ) as progress:
        for sample_id_chunk in batching.batched(
            items=annotation_sample_ids, batch_size=_ANNOTATION_EMBED_BATCH_SIZE
        ):
            try:
                stored += _embed_annotation_chunk(
                    session=session,
                    embedder=embedder,
                    model_id=model_id,
                    annotation_sample_ids=sample_id_chunk,
                )
            except AllInputFilesFailedError:
                if not skip_failed_chunks:
                    raise
                logger.warning(
                    "Skipping a chunk of %d crops where every file failed.", len(sample_id_chunk)
                )
            progress.update(len(sample_id_chunk))
    return stored


def _embed_image_chunk(
    session: Session,
    embedder: ImagePathEmbedder,
    model_id: UUID,
    sample_ids: list[UUID],
) -> int:
    """Fetches the paths of one chunk, embeds, stores and commits it.

    Images the embedder drops (see ``kept_indices``) are left out, so the stored sample
    ids stay aligned with the returned embeddings.

    Args:
        session: Database session for resolver operations.
        embedder: The image path embedder resolved for the collection.
        model_id: The model id the embeddings are stored under.
        sample_ids: The image sample ids in this chunk.

    Returns:
        The number of stored embeddings.

    Raises:
        ValueError: If the path of an image cannot be fetched.
    """
    sample_id_to_filepath = {
        image.sample_id: image.file_path_abs
        for image in image_resolver.get_many_by_id(session=session, sample_ids=sample_ids)
    }
    if len(sample_id_to_filepath) != len(sample_ids):
        raise ValueError("Could not fetch all image paths for the provided IDs.")

    result = embedder.embed_images(paths=[sample_id_to_filepath[id_] for id_ in sample_ids])
    kept_sample_ids = [sample_ids[index] for index in result.kept_indices]
    # embed_missing_images shows the progress, thus this function shows no storage bar
    embedding_storage.store_embeddings(
        session=session,
        model_id=model_id,
        sample_ids=kept_sample_ids,
        embeddings=result.embeddings,
        show_progress=False,
    )
    return len(kept_sample_ids)


def _embed_annotation_chunk(
    session: Session,
    embedder: ImageCropPathEmbedder,
    model_id: UUID,
    annotation_sample_ids: list[UUID],
) -> int:
    """Resolves the crops of one chunk, embeds, stores and commits it.

    Crops the embedder drops (see ``kept_indices``) are left out, so the stored sample
    ids stay aligned with the returned embeddings. Invalid crops are skipped when
    resolving.

    Args:
        session: Database session for resolver operations.
        embedder: The crop embedder resolved for the collection.
        model_id: The model id the embeddings are stored under.
        annotation_sample_ids: The annotation ids in this chunk.

    Returns:
        The number of stored embeddings.
    """
    annotation_crops = annotation_resolver.get_annotation_crops_for_ids(
        session=session, annotation_sample_ids=annotation_sample_ids
    )
    if not annotation_crops:
        return 0

    result = embedder.embed_image_crops(crops=[crop.image_crop for crop in annotation_crops])
    crop_sample_ids = [crop.annotation_sample_id for crop in annotation_crops]
    kept_sample_ids = [crop_sample_ids[index] for index in result.kept_indices]
    # embed_annotation_crops shows the progress, thus this function shows no storage bar
    embedding_storage.store_embeddings(
        session=session,
        model_id=model_id,
        sample_ids=kept_sample_ids,
        embeddings=result.embeddings,
        show_progress=False,
        replace=True,
    )
    return len(kept_sample_ids)
