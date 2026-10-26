"""Dataset-level embedding: embeds the samples of a collection that lack an embedding."""

from __future__ import annotations

from uuid import UUID

from lightly_studio_serve.embedder import ImagePathEmbedder
from sqlmodel import Session
from tqdm import tqdm

from lightly_studio.embed import default_embedder, embedding_storage
from lightly_studio.resolvers import collection_embedding_model_resolver, image_resolver
from lightly_studio.utils import batching

# Embed and commit images in chunks, so that an embedder failure keeps the earlier chunks
_IMAGE_EMBED_BATCH_SIZE = 1024


def embed_missing_images(session: Session, collection_id: UUID) -> int | None:
    """Embeds every image of the collection without an embedding of the default model.

    The selection runs before the embedder is resolved. Resolving registers a default
    model when the collection has none, so a collection without images to embed is left
    untouched.

    Args:
        session: Database session for resolver operations.
        collection_id: The collection whose images are embedded.

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
            stored += _embed_image_chunk(
                session=session,
                embedder=embedder,
                model_id=model_id,
                sample_ids=sample_id_chunk,
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
