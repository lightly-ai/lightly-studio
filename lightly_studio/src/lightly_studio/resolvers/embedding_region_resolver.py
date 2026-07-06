"""Resolve an embedding-plot region selection to the sample ids it encloses.

The frontend sends the lasso/rectangle geometry (a handful of vertices) instead of the full
list of selected sample ids, keeping the request body constant-size regardless of selection
size. Here we reproduce the exact client-side selection server-side: load the
cached, deterministic 2D projection the user lassoed over and run a vectorized point-in-polygon
test, then feed the resulting ids into the existing ``= ANY(...)`` filter path.
"""

from __future__ import annotations

from uuid import UUID

import numpy as np
from numpy.typing import NDArray
from sqlmodel import Session

from lightly_studio.models.embedding_region import EmbeddingRegion
from lightly_studio.resolvers import embedding_model_resolver, twodim_embedding_resolver
from lightly_studio.resolvers.image_filter import ImageFilter


def resolve_embedding_region(
    session: Session,
    collection_id: UUID,
    filters: ImageFilter | None,
) -> None:
    """Resolve any embedding region on an image ``filters`` to concrete sample ids, in place.

    No-op unless the filter carries a ``sample_filter.embedding_region``. Safe to call more
    than once. Must run before ``filters.apply(...)`` because the point-in-polygon test needs
    a database session that ``apply`` cannot access.
    """
    sample_filter = filters.sample_filter if filters is not None else None
    if sample_filter is None or sample_filter.embedding_region is None:
        return

    sample_ids = get_sample_ids_in_region(
        session=session,
        collection_id=collection_id,
        region=sample_filter.embedding_region,
    )
    sample_filter.set_resolved_region_sample_ids(sample_ids)


def get_sample_ids_in_region(
    session: Session,
    collection_id: UUID,
    region: EmbeddingRegion,
) -> list[UUID]:
    """Return the sample ids whose cached 2D coordinates fall inside ``region``."""
    # Resolve against the same deterministic default model as embeddings2d.get_2d_embeddings,
    # so the region is tested against the exact projection the user lassoed over.
    # TODO(Kondrat, 07/2026): Select the embedding model via API parameter once supported,
    # matching embeddings2d.get_2d_embeddings.
    embedding_model = embedding_model_resolver.get_default_by_collection_id(
        session=session,
        collection_id=collection_id,
    )
    if embedding_model is None:
        return []

    x_array, y_array, sample_ids = twodim_embedding_resolver.get_twodim_embeddings(
        session=session,
        collection_id=collection_id,
        embedding_model_id=embedding_model.embedding_model_id,
    )
    if len(sample_ids) == 0:
        return []

    inside_mask = _points_in_polygon(x=x_array, y=y_array, region=region)
    return [sample_id for sample_id, inside in zip(sample_ids, inside_mask) if inside]


def _points_in_polygon(
    x: NDArray[np.float32],
    y: NDArray[np.float32],
    region: EmbeddingRegion,
) -> NDArray[np.bool_]:
    """Vectorized even-odd ray-casting point-in-polygon test.

    Matches the frontend's ``isPointInPolygon`` (ray cast to the right, edges counted when
    exactly one endpoint is strictly above the point's y) so the server selects exactly the
    points the user saw highlighted.
    """
    vertices_x = np.asarray([vertex.x for vertex in region.polygon], dtype=np.float64)
    vertices_y = np.asarray([vertex.y for vertex in region.polygon], dtype=np.float64)

    px = np.asarray(x, dtype=np.float64)
    py = np.asarray(y, dtype=np.float64)

    inside = np.zeros(px.shape, dtype=np.bool_)

    # Previous vertex of each edge: (vertices[j], vertices[i]) with j = i - 1 (wrapping).
    prev_x = np.roll(vertices_x, 1)
    prev_y = np.roll(vertices_y, 1)

    for xi, yi, xj, yj in zip(vertices_x, vertices_y, prev_x, prev_y):
        # Edge straddles the horizontal ray at py (one endpoint strictly above, one not).
        straddles = (yi > py) != (yj > py)
        denominator = yj - yi
        # Guard against a horizontal edge (denominator == 0); those never straddle, so the
        # value used here is irrelevant, but avoid dividing by zero.
        safe_denominator = np.where(denominator == 0, 1.0, denominator)
        intersection_x = (xj - xi) * (py - yi) / safe_denominator + xi
        crosses = straddles & (px < intersection_x)
        inside ^= crosses

    return inside
