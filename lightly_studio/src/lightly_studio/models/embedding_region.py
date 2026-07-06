"""Geometry of an embedding-plot region selection.

The frontend sends the lasso/rectangle geometry (a handful of vertices, a few KB) instead
of the full list of selected sample ids. The backend reproduces the exact selection by
running point-in-polygon over the cached 2D projection, so the request body stays
constant-size regardless of how many points are selected (see LIG-9903).
"""

from __future__ import annotations

from pydantic import BaseModel, Field, field_validator

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

    polygon: list[Point2D] = Field(
        description="Ordered polygon vertices in embedding-plot data space (>= 3 vertices)."
    )

    @field_validator("polygon")
    @classmethod
    def _validate_polygon(cls, polygon: list[Point2D]) -> list[Point2D]:
        if len(polygon) < _MIN_POLYGON_VERTICES:
            raise ValueError("An embedding region polygon must have at least 3 vertices.")
        return polygon
