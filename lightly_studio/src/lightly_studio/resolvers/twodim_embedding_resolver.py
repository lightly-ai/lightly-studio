"""Handler for getting cached 2D embeddings from high-dimensional embeddings."""

from __future__ import annotations

from uuid import UUID

import numpy as np
from lightly_mundig import TwoDimEmbedding  # type: ignore[import-untyped]
from numpy.typing import NDArray
from sqlmodel import Session

from lightly_studio.models.embedding_model import EmbeddingModelTable
from lightly_studio.models.two_dim_embedding import TwoDimEmbeddingTable
from lightly_studio.resolvers import sample_embedding_resolver


def get_twodim_embeddings(
    session: Session,
    collection_id: UUID,
    embedding_model_id: UUID,
    reference_embeddings: list[list[float]] | None = None,
) -> tuple[NDArray[np.float32], NDArray[np.float32], list[UUID], list[tuple[float, float]]]:
    """Return cached 2D embeddings together with their sample identifiers.

    Uses a cache to avoid recomputing the 2D embeddings. The cache key combines the sorted
    sample identifiers with a deterministic 64-bit hash over the stored high-dimensional
    embeddings.

    If ``reference_embeddings`` is provided, also returns 2D centroids for each one. The
    centroids are not cached — on a 2D-projection cache hit we still load the high-dim
    embeddings to compute them (the expensive PacMap step is what the cache saves).

    Args:
        session: Database session.
        collection_id: Collection identifier.
        embedding_model_id: Embedding model identifier.
        reference_embeddings: Optional list of high-dim reference embeddings to project
            into the plot as marker centroids.

    Returns:
        Tuple of (x coordinates, y coordinates, ordered sample IDs, reference centroids).
    """
    embedding_model = session.get(EmbeddingModelTable, embedding_model_id)
    if embedding_model is None:
        raise ValueError(f"Embedding model {embedding_model_id} not found.")

    # Check if we have a cached 2D embedding for the given collection and embedding model.
    cache_key, sample_ids_of_samples_with_embeddings = (
        sample_embedding_resolver.get_hash_by_collection_id(
            session=session,
            collection_id=collection_id,
            embedding_model_id=embedding_model_id,
        )
    )

    if not sample_ids_of_samples_with_embeddings:
        empty = np.array([], dtype=np.float32)
        return empty, empty, [], []

    # If there is a cached entry, return it (optionally with freshly-computed centroids).
    cached = session.get(TwoDimEmbeddingTable, cache_key)
    if cached is not None:
        x_values = np.array(cached.x, dtype=np.float32)
        y_values = np.array(cached.y, dtype=np.float32)
        centroids: list[tuple[float, float]] = []
        if reference_embeddings:
            ordered_ids, image_matrix = _load_image_matrix(
                session=session,
                collection_id=collection_id,
                embedding_model_id=embedding_model_id,
            )
            if image_matrix.shape[0] > 0:
                sample_ids_of_samples_with_embeddings = ordered_ids
                centroids = _compute_reference_centroids(
                    image_matrix=image_matrix,
                    x_values=x_values,
                    y_values=y_values,
                    reference_embeddings=reference_embeddings,
                )
        return x_values, y_values, sample_ids_of_samples_with_embeddings, centroids

    # No cached 2D entry — load the high-dimensional embeddings (cached in-process) and
    # compute the PacMap projection.
    sample_ids_of_samples_with_embeddings, image_matrix = _load_image_matrix(
        session=session,
        collection_id=collection_id,
        embedding_model_id=embedding_model_id,
    )
    if image_matrix.shape[0] == 0:
        empty = np.array([], dtype=np.float32)
        return empty, empty, [], []

    planar_embeddings = _calculate_2d_embeddings(image_matrix.tolist())
    embeddings_2d = np.asarray(planar_embeddings, dtype=np.float32)
    x_values, y_values = embeddings_2d[:, 0], embeddings_2d[:, 1]

    # Write the computed 2D embeddings to the cache.
    cache_entry = TwoDimEmbeddingTable(hash=cache_key, x=list(x_values), y=list(y_values))
    session.add(cache_entry)
    session.commit()

    centroids = _compute_reference_centroids(
        image_matrix=image_matrix,
        x_values=x_values,
        y_values=y_values,
        reference_embeddings=reference_embeddings or [],
    )

    return x_values, y_values, sample_ids_of_samples_with_embeddings, centroids


REFERENCE_TOP_K_MAX = 20
REFERENCE_TOP_K_FRACTION = 20  # 1/20 = 5% of samples


# Scrappy in-process cache of high-dim image embeddings. Demo-only — assumes the underlying
# embeddings do not change for the lifetime of the process. Restart the server to refresh.
_image_matrix_cache: dict[tuple[UUID, UUID], tuple[list[UUID], NDArray[np.float32]]] = {}


def _load_image_matrix(
    session: Session,
    collection_id: UUID,
    embedding_model_id: UUID,
) -> tuple[list[UUID], NDArray[np.float32]]:
    """Return (ordered sample_ids, image_matrix) for a collection, cached in memory."""
    key = (collection_id, embedding_model_id)
    cached = _image_matrix_cache.get(key)
    if cached is not None:
        return cached

    empty_matrix: NDArray[np.float32] = np.zeros((0, 0), dtype=np.float32)
    _, sample_ids_with_embeddings = sample_embedding_resolver.get_hash_by_collection_id(
        session=session,
        collection_id=collection_id,
        embedding_model_id=embedding_model_id,
    )
    if not sample_ids_with_embeddings:
        _image_matrix_cache[key] = ([], empty_matrix)
        return _image_matrix_cache[key]

    sample_embeddings = sample_embedding_resolver.get_by_sample_ids(
        session=session,
        sample_ids=sample_ids_with_embeddings,
        embedding_model_id=embedding_model_id,
    )
    if not sample_embeddings:
        _image_matrix_cache[key] = ([], empty_matrix)
        return _image_matrix_cache[key]

    ordered_ids = [embedding.sample_id for embedding in sample_embeddings]
    image_matrix = np.asarray(
        [embedding.embedding for embedding in sample_embeddings], dtype=np.float32
    )
    _image_matrix_cache[key] = (ordered_ids, image_matrix)
    return _image_matrix_cache[key]


def _compute_reference_centroids(
    image_matrix: NDArray[np.float32],
    x_values: NDArray[np.float32],
    y_values: NDArray[np.float32],
    reference_embeddings: list[list[float]],
) -> list[tuple[float, float]]:
    """Return 2D centroids for each reference embedding.

    For each reference, take the top-K most cosine-similar samples in the original
    high-dim space and return the mean of their already-computed 2D projections.
    K is adaptive: ``min(5% of samples, 20)`` with a floor of 1.
    """
    n_samples = image_matrix.shape[0]
    if not reference_embeddings or n_samples == 0:
        return []
    refs = np.asarray(reference_embeddings, dtype=np.float32)
    image_norms = np.maximum(np.linalg.norm(image_matrix, axis=1), 1e-9)
    ref_norms = np.maximum(np.linalg.norm(refs, axis=1), 1e-9)
    sims = (refs @ image_matrix.T) / np.outer(ref_norms, image_norms)
    k = max(1, min(REFERENCE_TOP_K_MAX, n_samples // REFERENCE_TOP_K_FRACTION))
    centroids: list[tuple[float, float]] = []
    for ref_idx in range(refs.shape[0]):
        top_idx = np.argpartition(-sims[ref_idx], k - 1)[:k]
        centroids.append((float(x_values[top_idx].mean()), float(y_values[top_idx].mean())))
    return centroids


def get_twodim_embeddings_nlp(  # noqa: PLR0913
    session: Session,
    collection_id: UUID,
    embedding_model_id: UUID,
    direction_x: list[float],
    direction_y: list[float],
    reference_embeddings: list[list[float]] | None = None,
) -> tuple[NDArray[np.float32], NDArray[np.float32], list[UUID], list[tuple[float, float]]]:
    """Return 2D embeddings by projecting onto two natural-language axis directions.

    Prototype for LIG-9502 Variant A. Each axis direction is supplied by the caller and is
    typically either a raw text embedding (single anchor) or a contrastive difference
    ``embed(positive) - embed(negative)`` (concept axis). Image embeddings are projected via
    dot product. No caching — text inputs change frequently.

    If ``reference_embeddings`` is provided, also returns 2D centroids for each one: for
    each reference, take the top-K most cosine-similar sample embeddings (in the original
    high-dimensional space) and return the mean of their already-computed 2D projections.
    Used to place "reference" markers inside the data cloud at the location where each
    concept actually manifests in the data.
    """
    embedding_model = session.get(EmbeddingModelTable, embedding_model_id)
    if embedding_model is None:
        raise ValueError(f"Embedding model {embedding_model_id} not found.")

    sample_ids, image_matrix = _load_image_matrix(
        session=session,
        collection_id=collection_id,
        embedding_model_id=embedding_model_id,
    )
    if image_matrix.shape[0] == 0:
        empty = np.array([], dtype=np.float32)
        return empty, empty, [], []

    directions = np.asarray([direction_x, direction_y], dtype=np.float32)
    projected = image_matrix @ directions.T
    x_values = np.ascontiguousarray(projected[:, 0], dtype=np.float32)
    y_values = np.ascontiguousarray(projected[:, 1], dtype=np.float32)

    centroids = _compute_reference_centroids(
        image_matrix=image_matrix,
        x_values=x_values,
        y_values=y_values,
        reference_embeddings=reference_embeddings or [],
    )

    return x_values, y_values, sample_ids, centroids


def get_twodim_embeddings_pca(
    session: Session,
    collection_id: UUID,
    embedding_model_id: UUID,
    text_embeddings: list[list[float]],
    reference_embeddings: list[list[float]] | None = None,
) -> tuple[NDArray[np.float32], NDArray[np.float32], list[UUID], list[tuple[float, float]]]:
    """Return 2D embeddings by PCA-projecting onto the top 2 directions of text embeddings.

    Prototype for LIG-9502 Variant B: ≥2 texts. Text embeddings are mean-centered, then SVD
    extracts the top 2 right singular vectors; image embeddings are projected onto those.
    No caching — text inputs change frequently.

    If ``reference_embeddings`` is provided, also returns 2D centroids for each one: for
    each reference, take the top-K most cosine-similar samples in the original high-dim
    space and return the mean of their 2D projections.
    """
    embedding_model = session.get(EmbeddingModelTable, embedding_model_id)
    if embedding_model is None:
        raise ValueError(f"Embedding model {embedding_model_id} not found.")
    if len(text_embeddings) < 2:  # noqa: PLR2004
        raise ValueError("PCA projection requires at least 2 text embeddings.")

    sample_ids, image_matrix = _load_image_matrix(
        session=session,
        collection_id=collection_id,
        embedding_model_id=embedding_model_id,
    )
    if image_matrix.shape[0] == 0:
        empty = np.array([], dtype=np.float32)
        return empty, empty, [], []

    texts = np.asarray(text_embeddings, dtype=np.float32)
    texts_centered = texts - texts.mean(axis=0)
    # SVD returns right singular vectors in Vt (shape (k, D)); take the top 2 directions.
    _, _, vt = np.linalg.svd(texts_centered, full_matrices=False)
    directions = vt[:2]

    projected = image_matrix @ directions.T
    x_values = np.ascontiguousarray(projected[:, 0], dtype=np.float32)
    y_values = np.ascontiguousarray(projected[:, 1], dtype=np.float32)

    centroids = _compute_reference_centroids(
        image_matrix=image_matrix,
        x_values=x_values,
        y_values=y_values,
        reference_embeddings=reference_embeddings or [],
    )

    return x_values, y_values, sample_ids, centroids


def _calculate_2d_embeddings(embedding_values: list[list[float]]) -> list[tuple[float, float]]:
    n_samples = len(embedding_values)
    # For 0, 1 or 2 samples we hard-code deterministic coordinates.
    if n_samples == 0:
        return []
    if n_samples == 1:
        return [(0.0, 0.0)]
    if n_samples == 2:  # noqa: PLR2004
        return [(0.0, 0.0), (1.0, 1.0)]

    embedding_calculator = TwoDimEmbedding(embedding_values)
    return embedding_calculator.calculate_2d_embedding()  # type: ignore[no-any-return]
