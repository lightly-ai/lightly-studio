"""Axes of an embedding plot that is a linear projection of the embeddings."""

from __future__ import annotations

from pydantic import BaseModel, Field


class ProjectionAxes(BaseModel):
    """Two directions in embedding space that define the plot axes.

    The plot x and y values of a sample are the dot products of its embedding with ``x`` and
    ``y``. The frontend sends the same object with the plot request and with a region drawn on
    that plot, so both use the same coordinates.
    """

    x: list[float] = Field(min_length=1, description="X axis direction in embedding space")
    y: list[float] = Field(min_length=1, description="Y axis direction in embedding space")
