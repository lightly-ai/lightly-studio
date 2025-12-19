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

    # Define a fixed order of sample IDs for the cache key.
    sample_ids_ordered = list(
        session.exec(
            select(SampleTable.sample_id)
            .where(SampleTable.collection_id == collection_id)
            .order_by(col(SampleTable.sample_id).asc())
        ).all()
    )

    # Check if we have a cached 2D embedding for the given samples and embedding model.
    # The order is defined by sample_ids_ordered.
    cache_key, sample_ids_of_samples_with_embeddings = (
        sample_embedding_resolver.get_hash_by_sample_ids(
            session=session,
            sample_ids_ordered=sample_ids_ordered,
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
