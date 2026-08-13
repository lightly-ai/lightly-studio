"""Handler for getting cached 2D embeddings from high-dimensional embeddings."""

from __future__ import annotations

from uuid import UUID

import numpy as np
from lightly_mundig import TwoDimEmbedding  # type: ignore[import-untyped]
from numpy.typing import NDArray
from sqlmodel import Session

from lightly_studio.database.db_vector import Embedding
from lightly_studio.models.embedding_model import EmbeddingModelTable
from lightly_studio.models.two_dim_embedding import TwoDimEmbeddingTable
from lightly_studio.resolvers import sample_embedding_resolver


def get_twodim_embeddings(
    session: Session,
    collection_id: UUID,
    embedding_model_id: UUID,
) -> tuple[NDArray[np.float32], NDArray[np.float32], list[UUID]]:
    """Return cached 2D embeddings together with their sample identifiers.

    The projection is cached per (collection, embedding model). The cached row stores the
    sample ids next to the coordinates, so a cache hit never has to re-read
    ``sample_embedding``. A fingerprint over the collection's embeddings decides whether
    the cached entry still describes the current set of samples.

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

    sample_count, fingerprint = sample_embedding_resolver.get_fingerprint_by_collection_id(
        session=session,
        collection_id=collection_id,
        embedding_model_id=embedding_model_id,
    )
    if sample_count == 0:
        empty = np.array([], dtype=np.float32)
        return empty, empty, []

    # The length check guards against a corrupted row: the three arrays are written
    # together and should never diverge, but callers zip the coordinates with the ids, so
    # a mismatch is treated as a miss rather than propagated.
    cached = session.get(TwoDimEmbeddingTable, (collection_id, embedding_model_id))
    if (
        cached is not None
        and cached.fingerprint == fingerprint
        and len(cached.sample_ids) == len(cached.x) == len(cached.y)
    ):
        return (
            np.array(cached.x, dtype=np.float32),
            np.array(cached.y, dtype=np.float32),
            list(cached.sample_ids),
        )

    # Cache miss or stale entry: load the high-dimensional embeddings and reproject.
    sample_embeddings = sample_embedding_resolver.get_all_by_collection_id(
        session=session,
        collection_id=collection_id,
        embedding_model_id=embedding_model_id,
    )
    if not sample_embeddings:
        empty = np.array([], dtype=np.float32)
        return empty, empty, []

    # The order is the one get_all_by_collection_id produced, not the fingerprint's
    # canonical sample_id order. Both the coordinates and the stored ids follow it.
    sample_ids = [embedding.sample_id for embedding in sample_embeddings]
    embedding_values = [embedding.embedding for embedding in sample_embeddings]
    planar_embeddings = _calculate_2d_embeddings(embedding_values)
    embeddings_2d = np.asarray(planar_embeddings, dtype=np.float32)
    x_values, y_values = embeddings_2d[:, 0], embeddings_2d[:, 1]

    # merge() rather than add(): recomputing over an existing key must overwrite the row
    # in place instead of raising an IntegrityError.
    session.merge(
        TwoDimEmbeddingTable(
            collection_id=collection_id,
            embedding_model_id=embedding_model_id,
            fingerprint=fingerprint,
            sample_ids=sample_ids,
            x=[float(value) for value in x_values],
            y=[float(value) for value in y_values],
        )
    )
    session.commit()

    return x_values, y_values, sample_ids


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
