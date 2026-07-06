"""Geometry of an embedding-plot region selection.

The frontend sends the lasso/rectangle geometry (a handful of vertices, a few KB) instead
of the full list of selected sample ids. The backend reproduces the exact selection by
running point-in-polygon over the cached 2D projection, so the request body stays
constant-size regardless of how many points are selected.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

# A polygon needs at least three vertices to enclose any area.
_MIN_POLYGON_VERTICES = 3


class Point2D(BaseModel):
    """A single vertex in embedding-plot (raw data) coordinate space."""

    x: float
    y: float


class EmbeddingRegion(BaseModel):
    """A closed region in embedding-plot space, expressed as polygon vertices.

    Rectangle selections are normalized to their four corner vertices on the frontend, so
    both lasso and rectangle selections arrive here as a polygon. Coordinates are in the
    same raw data space as the cached 2D projection, so no additional transform is needed
    before the point-in-polygon test.
    """

    # Declaring the constraint on the field (not a custom validator) keeps runtime validation,
    # the generated OpenAPI schema (`minItems`), and generated clients in sync.
    polygon: list[Point2D] = Field(
        min_length=_MIN_POLYGON_VERTICES,
        description="Ordered polygon vertices in embedding-plot data space (>= 3 vertices).",
    )
