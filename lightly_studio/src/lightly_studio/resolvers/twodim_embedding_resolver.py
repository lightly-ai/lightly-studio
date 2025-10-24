"""Handler for getting cached 2D embeddings from high-dimensional embeddings."""

from __future__ import annotations

from uuid import UUID

import numpy as np
from lightly_mundig import TwoDimEmbedding  # type: ignore[import-untyped]
from numpy.typing import NDArray
from sqlmodel import Session, col, select

from lightly_studio.dataset.env import LIGHTLY_STUDIO_LICENSE_KEY
from lightly_studio.models.embedding_model import EmbeddingModelTable
from lightly_studio.models.sample import SampleTable
from lightly_studio.models.two_dim_embedding import TwoDimEmbeddingTable
from lightly_studio.resolvers import sample_embedding_resolver


def get_twodim_embeddings(
    session: Session,
    dataset_id: UUID,
    embedding_model_id: UUID,
) -> tuple[NDArray[np.float32], NDArray[np.float32], list[UUID]]:
    """Return cached 2D embeddings together with their sample identifiers.

    Uses a cache to avoid recomputing the 2D embeddings. The cache key combines the sorted
    sample identifiers with a deterministic 64-bit hash over the stored high-dimensional
    embeddings.

    Args:
        session: Database session.
        dataset_id: Dataset identifier.
        embedding_model_id: Embedding model identifier.

    Returns:
        Tuple of (x coordinates, y coordinates, ordered sample IDs).
    """
    embedding_model = session.get(EmbeddingModelTable, embedding_model_id)
    if embedding_model is None:
        raise ValueError(f"Embedding model {embedding_model_id} not found.")

    sample_ids_set = set(
        session.exec(
            select(SampleTable.sample_id)
            .where(SampleTable.dataset_id == dataset_id)
            .order_by(col(SampleTable.created_at).asc(), col(SampleTable.sample_id).asc())
        ).all()
    )
    cache_key = sample_embedding_resolver.get_hash_by_sample_ids(
        session=session,
        sample_ids=sample_ids_set,
        embedding_model_id=embedding_model_id,
    )

    cached = session.get(TwoDimEmbeddingTable, cache_key)
    if cached is not None:
        x_values = np.array(cached.x, dtype=np.float32)
        y_values = np.array(cached.y, dtype=np.float32)
        return x_values, y_values, list(sample_ids_set)

    sample_embeddings = sample_embedding_resolver.get_by_sample_ids(
        session=session,
        sample_ids=list(sample_ids_set),
        embedding_model_id=embedding_model_id,
    )
    sample_embeddings = sorted(sample_embeddings, key=lambda e: e.sample_id)

    if not sample_embeddings:
        empty = np.array([], dtype=np.float32)
        return empty, empty, []

    sample_ids = [embedding.sample_id for embedding in sample_embeddings]

    # Otherwise, compute the 2D embedding from the high-dimensional embeddings.
    embedding_values = [embedding.embedding for embedding in sample_embeddings]

    planar_embeddings = _calculate_2d_embeddings(embedding_values)
    embeddings_2d = np.asarray(planar_embeddings, dtype=np.float32)
    x_values, y_values = embeddings_2d[:, 0], embeddings_2d[:, 1]

    # Write the computed 2D embeddings to the cache.
    cache_entry = TwoDimEmbeddingTable(hash=cache_key, x=list(x_values), y=list(y_values))
    session.add(cache_entry)
    session.commit()

    return x_values, y_values, sample_ids


def _calculate_2d_embeddings(embedding_values: list[list[float]]) -> list[tuple[float, float]]:
    n_samples = len(embedding_values)
    # For 0, 1 or 2 samples we hard-code deterministic coordinates.
    if n_samples == 0:
        return []
    if n_samples == 1:
        return [(0.0, 0.0)]
    if n_samples == 2:  # noqa: PLR2004
        return [(0.0, 0.0), (1.0, 1.0)]

    license_key = LIGHTLY_STUDIO_LICENSE_KEY
    if license_key is None:
        raise ValueError(
            "LIGHTLY_STUDIO_LICENSE_KEY environment variable is not set. "
            "Please set it to your LightlyStudio license key."
        )
    embedding_calculator = TwoDimEmbedding(embedding_values, license_key)
    return embedding_calculator.calculate_2d_embedding()  # type: ignore[no-any-return]
