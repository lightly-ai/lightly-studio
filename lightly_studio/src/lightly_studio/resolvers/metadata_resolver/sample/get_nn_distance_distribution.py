"""Resolver computing the distribution of nearest-neighbor Euclidean distance.

For every embedded sample in a *scope* this finds the Euclidean distance to its most
similar *other* sample **within that same scope**, then bins those values into an
equal-width numeric histogram. The result reuses the ``MetadataDistributionView``
numeric shape so the frontend renders it like any other numeric metadata distribution.

Several scopes (e.g. the current selection plus one per compared tag) are computed
together in a single call so the neighbor search for each series stays restricted to
its own samples — small per-tag matrices instead of the full collection every time —
and so all series can share one set of bin edges spanning the union of their values.
That shared x-axis is what lets the overlaid histograms line up, and matches the
behavior of an external plugin computing nearest-neighbor distances per tag.
"""

from __future__ import annotations

from uuid import UUID

import numpy as np
from numpy.typing import NDArray
from sqlmodel import Session

from lightly_studio.models.embedding_model import EmbeddingModelTable
from lightly_studio.models.metadata import MetadataDistributionView
from lightly_studio.resolvers import embedding_model_resolver, sample_embedding_resolver
from lightly_studio.resolvers.metadata_resolver.sample.get_metadata_distribution import (
    DEFAULT_BINS,
    bin_counts,
    build_bin_edges,
)

# Key surfaced in the response; the frontend uses it purely as a label.
NN_DISTANCE_KEY = "nn_distance"

# Rows processed per matmul block when searching for nearest neighbors. Keeps the
# distance computation to at most (CHUNK x N) floats in memory instead of N x N,
# so it scales to large pools without allocating a huge dense matrix.
_CHUNK = 1024

# A neighbor search needs at least two embeddings (a point and one other).
_MIN_EMBEDDINGS = 2


def get_nn_distance_distributions(
    session: Session,
    collection_id: UUID,
    *,
    scopes: list[set[UUID] | None],
    bins: int = DEFAULT_BINS,
    embedding_model_name: str | None = None,
) -> list[MetadataDistributionView]:
    """Compute nearest-neighbor distance histograms for several scopes at once.

    Each entry in ``scopes`` becomes one histogram: distances are computed among the
    samples of that scope only. All returned histograms share the same bin edges,
    spanning the union of every scope's values, so the frontend can overlay them on a
    single x-axis.

    Args:
        session: The database session.
        collection_id: The collection's UUID.
        scopes: One sample-id set per series, in display order. A ``None`` entry means
            the whole collection. An empty list yields an empty result.
        bins: Number of equal-width bins for the shared histogram.
        embedding_model_name: Embedding model name; uses the collection default when
            ``None``.

    Returns:
        One numeric ``MetadataDistributionView`` per scope, aligned to ``scopes`` order
        and sharing bin edges. When the collection has no embedding model, every view is
        empty (empty ``bin_edges``/``counts``) so the panel shows a "no data" state.
    """
    if not scopes:
        return []

    embedding_model = _resolve_embedding_model(
        session=session,
        collection_id=collection_id,
        embedding_model_name=embedding_model_name,
    )
    if embedding_model is None:
        return [_empty_view(none_count=len(scope) if scope else 0) for scope in scopes]

    rows = sample_embedding_resolver.get_all_by_collection_id(
        session=session,
        collection_id=collection_id,
        embedding_model_id=embedding_model.embedding_model_id,
    )
    embedding_by_id = {row.sample_id: row.embedding for row in rows}

    # Distances and none-count per series; bin edges are derived once from the union.
    per_series: list[tuple[list[float], int]] = [
        _distances_for_scope(scope=scope, embedding_by_id=embedding_by_id) for scope in scopes
    ]

    all_values = [value for values, _ in per_series for value in values]
    bin_edges = build_bin_edges(global_values=all_values, bins=bins)

    return [
        MetadataDistributionView(
            key=NN_DISTANCE_KEY,
            type="float",
            kind="numeric",
            bin_edges=bin_edges,
            counts=bin_counts(values=values, bin_edges=bin_edges),
            none_count=none_count,
        )
        for values, none_count in per_series
    ]


def _distances_for_scope(
    scope: set[UUID] | None,
    embedding_by_id: dict[UUID, NDArray[np.float32]],
) -> tuple[list[float], int]:
    """Return ``(nn_distances, none_count)`` for a single scope.

    ``none_count`` is the number of in-scope samples that received no distance: those
    without an embedding, or (when the scope has fewer than two embeddings) all of them,
    since a neighbor can only be found among at least two embedded samples.
    """
    if scope is None:
        scoped_embeddings = list(embedding_by_id.values())
        missing = 0
    else:
        scoped_embeddings = [
            embedding_by_id[sample_id] for sample_id in scope if sample_id in embedding_by_id
        ]
        missing = len(scope) - len(scoped_embeddings)

    if len(scoped_embeddings) < _MIN_EMBEDDINGS:
        # No neighbor exists within the scope, so no sample gets a value.
        return [], missing + len(scoped_embeddings)

    embeddings = np.asarray(scoped_embeddings, dtype=np.float32)
    distances = _nearest_neighbor_distance(embeddings=embeddings)
    return distances.tolist(), missing


def _resolve_embedding_model(
    session: Session,
    collection_id: UUID,
    embedding_model_name: str | None,
) -> EmbeddingModelTable | None:
    """Resolve the embedding model, returning ``None`` when none exists."""
    if embedding_model_name is not None:
        return embedding_model_resolver.get_by_name(
            session=session,
            collection_id=collection_id,
            embedding_model_name=embedding_model_name,
        )
    return embedding_model_resolver.get_default_by_collection_id(
        session=session, collection_id=collection_id
    )


def _empty_view(none_count: int) -> MetadataDistributionView:
    """Return an empty numeric view for scopes without enough embeddings."""
    return MetadataDistributionView(
        key=NN_DISTANCE_KEY,
        type="float",
        kind="numeric",
        bin_edges=[],
        counts=[],
        none_count=none_count,
    )


def _nearest_neighbor_distance(embeddings: NDArray[np.float32]) -> NDArray[np.float32]:
    """Return each row's Euclidean distance to its nearest *other* row.

    Computed block-by-block (``_CHUNK`` rows at a time) to avoid materializing the
    full N x N distance matrix. Self-matches are excluded so a point never picks
    itself as its own neighbor.
    """
    n = embeddings.shape[0]
    # Squared L2 norm of every row, reused across blocks for the identity
    # ||a - b||^2 = ||a||^2 + ||b||^2 - 2 a . b.
    squared_norms = np.sum(embeddings**2, axis=1)

    nn_distance = np.empty(n, dtype=np.float32)
    for start in range(0, n, _CHUNK):
        stop = min(start + _CHUNK, n)
        # (chunk, N) squared distances of this block against every embedding.
        sq_dists = (
            squared_norms[start:stop, None]
            + squared_norms[None, :]
            - 2.0 * (embeddings[start:stop] @ embeddings.T)
        )
        # Floating-point noise can drive equal-vector distances slightly negative.
        np.maximum(sq_dists, 0.0, out=sq_dists)
        # Mask self-matches so a point never picks itself as its own neighbor.
        sq_dists[np.arange(stop - start), np.arange(start, stop)] = np.inf
        nn_distance[start:stop] = np.sqrt(np.min(sq_dists, axis=1))

    return nn_distance
