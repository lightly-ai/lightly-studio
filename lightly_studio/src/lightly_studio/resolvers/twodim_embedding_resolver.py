"""Handler for getting cached 2D embeddings from high-dimensional embeddings."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from uuid import UUID

import numpy as np
from lightly_mundig import TwoDimEmbedding  # type: ignore[import-untyped]
from numpy.typing import NDArray
from sqlmodel import Session

from lightly_studio.database.db_vector import Embedding
from lightly_studio.models.embedding_model import EmbeddingModelTable
from lightly_studio.models.two_dim_embedding import TwoDimEmbeddingTable
from lightly_studio.resolvers import sample_embedding_resolver


@dataclass(frozen=True)
class _ImageMatrix:
    """The high-dimensional embeddings of a collection, kept in memory.

    N is the number of samples with an embedding and D is the embedding dimension.

    Attributes:
        embedding_hash: The hash of the stored embeddings when they were loaded.
        sample_ids: The ordered sample IDs of the rows of ``matrix``.
        matrix: The embeddings of shape (N, D).
    """

    embedding_hash: str
    sample_ids: list[UUID]
    matrix: NDArray[np.float32]


# One entry for each (collection_id, embedding_model_id). An entry is loaded again when the hash
# of the stored embeddings changes, for example after new samples are embedded.
_image_matrix_cache: dict[tuple[UUID, UUID], _ImageMatrix] = {}


def get_twodim_embeddings(
    session: Session,
    collection_id: UUID,
    embedding_model_id: UUID,
) -> tuple[NDArray[np.float32], NDArray[np.float32], list[UUID]]:
    """Return cached 2D embeddings together with their sample identifiers.

    Uses a cache to avoid recomputing the 2D embeddings. The cache key combines the sorted
    sample identifiers with a deterministic 64-bit hash over the stored high-dimensional
    embeddings.

    Args:
        session: Database session.
        collection_id: Collection identifier.
        embedding_model_id: Embedding model identifier.

    Returns:
        Tuple of (x coordinates, y coordinates, ordered sample IDs).
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
        return empty, empty, []

    # If there is a cached entry, return it.
    cached = session.get(TwoDimEmbeddingTable, cache_key)
    if cached is not None:
        x_values = np.array(cached.x, dtype=np.float32)
        y_values = np.array(cached.y, dtype=np.float32)
        return x_values, y_values, sample_ids_of_samples_with_embeddings

    # No cached entry found - load the high-dimensional embeddings.
    # The order is defined by sample_ids_of_samples_with_embeddings.
    sample_embeddings = sample_embedding_resolver.get_by_sample_ids(
        session=session,
        sample_ids=sample_ids_of_samples_with_embeddings,
        embedding_model_id=embedding_model_id,
    )

    # If there are no embeddings, return empty arrays.
    if not sample_embeddings:
        empty = np.array([], dtype=np.float32)
        return empty, empty, []

    # Compute the 2D embedding from the high-dimensional embeddings.
    # The order is now defined by sample_embeddings. They are the ordered subset of the
    # sample_ids_of_samples_with_embeddings that have embeddings.
    sample_ids_of_samples_with_embeddings = [embedding.sample_id for embedding in sample_embeddings]
    embedding_values = [embedding.embedding for embedding in sample_embeddings]
    planar_embeddings = _calculate_2d_embeddings(embedding_values)
    embeddings_2d = np.asarray(planar_embeddings, dtype=np.float32)
    x_values, y_values = embeddings_2d[:, 0], embeddings_2d[:, 1]

    # Write the computed 2D embeddings to the cache.
    cache_entry = TwoDimEmbeddingTable(hash=cache_key, x=list(x_values), y=list(y_values))
    session.add(cache_entry)
    session.commit()

    return x_values, y_values, sample_ids_of_samples_with_embeddings


def get_twodim_embeddings_from_axes(
    session: Session,
    collection_id: UUID,
    embedding_model_id: UUID,
    direction_x: Sequence[float],
    direction_y: Sequence[float],
) -> tuple[NDArray[np.float32], NDArray[np.float32], list[UUID]]:
    """Return 2D embeddings that are projections onto two axis directions.

    D is the embedding dimension. The x and y values of a sample are the dot products of its
    embedding with ``direction_x`` and ``direction_y``. The values are not rescaled, so the
    spread of an axis shows how much the samples vary along its direction.

    The result is not stored in the database, because the directions change with each query.
    The high-dimensional embeddings stay in memory until they change.

    Args:
        session: Database session.
        collection_id: Collection identifier.
        embedding_model_id: Embedding model identifier.
        direction_x: The X axis direction of shape (D,).
        direction_y: The Y axis direction of shape (D,).

    Returns:
        Tuple of (x coordinates, y coordinates, ordered sample IDs).

    Raises:
        ValueError: If the embedding model does not exist, or if a direction does not have
            the embedding dimension.
    """
    embedding_model = session.get(EmbeddingModelTable, embedding_model_id)
    if embedding_model is None:
        raise ValueError(f"Embedding model {embedding_model_id} not found.")
    dimension = embedding_model.embedding_dimension
    if len(direction_x) != dimension or len(direction_y) != dimension:
        raise ValueError(
            f"The axis directions must have the embedding dimension {dimension}, "
            f"got {len(direction_x)} and {len(direction_y)}."
        )

    image_matrix = _load_image_matrix(
        session=session,
        collection_id=collection_id,
        embedding_model_id=embedding_model_id,
    )
    if not image_matrix.sample_ids:
        empty = np.array([], dtype=np.float32)
        return empty, empty, []

    directions = np.asarray([direction_x, direction_y], dtype=np.float32)
    projected = image_matrix.matrix @ directions.T
    x_values = np.ascontiguousarray(projected[:, 0], dtype=np.float32)
    y_values = np.ascontiguousarray(projected[:, 1], dtype=np.float32)
    return x_values, y_values, image_matrix.sample_ids


def _calculate_2d_embeddings(
    embedding_values: list[Embedding],
) -> list[tuple[float, float]]:
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


def _load_image_matrix(
    session: Session,
    collection_id: UUID,
    embedding_model_id: UUID,
) -> _ImageMatrix:
    """Return the embeddings of a collection, from memory if they did not change."""
    embedding_hash, sample_ids_with_embeddings = (
        sample_embedding_resolver.get_hash_by_collection_id(
            session=session,
            collection_id=collection_id,
            embedding_model_id=embedding_model_id,
        )
    )
    key = (collection_id, embedding_model_id)
    cached = _image_matrix_cache.get(key)
    if cached is not None and cached.embedding_hash == embedding_hash:
        return cached

    sample_embeddings = sample_embedding_resolver.get_by_sample_ids(
        session=session,
        sample_ids=sample_ids_with_embeddings,
        embedding_model_id=embedding_model_id,
    )
    image_matrix = _ImageMatrix(
        embedding_hash=embedding_hash,
        sample_ids=[embedding.sample_id for embedding in sample_embeddings],
        matrix=np.asarray(
            [embedding.embedding for embedding in sample_embeddings], dtype=np.float32
        ),
    )
    _image_matrix_cache[key] = image_matrix
    return image_matrix
