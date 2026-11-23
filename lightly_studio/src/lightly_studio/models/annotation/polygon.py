"""Polygon annotation models.

A polygon has one or more parts. Each part is a closed ring of vertices in float pixels of the
original image, with the origin at the top-left corner.
"""

import math
from collections.abc import Sequence
from dataclasses import dataclass
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import JSON, Column
from sqlalchemy.orm import Mapped
from sqlmodel import Field, Relationship, SQLModel

if TYPE_CHECKING:
    from lightly_studio.models.annotation.annotation_base import (
        AnnotationBaseTable,
    )
else:
    AnnotationBaseTable = object

# Vertices are rounded to 0.001 px. The lost precision cannot be seen.
COORDINATE_DECIMALS = 3
MIN_VERTICES_PER_PART = 3

Polygons = list[list[tuple[float, float]]]
# The JSON column returns lists, so the storage type uses lists for vertices too.
StoredPolygons = list[list[list[float]]]


@dataclass(frozen=True)
class ValidatedPolygons:
    """Rounded polygon parts and the integer bounding box that contains all vertices."""

    polygons: StoredPolygons
    x: int
    y: int
    width: int
    height: int


class PolygonAnnotationTable(SQLModel, table=True):
    """Database table model for polygon annotations."""

    __tablename__ = "polygon_annotation"

    sample_id: UUID = Field(
        default_factory=uuid4,
        primary_key=True,
        foreign_key="annotation_base.sample_id",
    )

    annotation_base: Mapped["AnnotationBaseTable"] = Relationship(back_populates="polygon_details")

    x: int
    y: int
    width: int
    height: int
    polygons: StoredPolygons = Field(sa_column=Column(JSON, nullable=False))


class PolygonAnnotationView(SQLModel):
    """API response model for polygon annotations."""

    x: int
    y: int
    width: int
    height: int
    polygons: Polygons


def validate_polygons(polygons: Sequence[Sequence[Sequence[float]]]) -> ValidatedPolygons:
    """Validate and round polygon parts, then compute their bounding box.

    The bounding box is rounded outward, so it contains every vertex.

    Args:
        polygons: The polygon parts. Each part is a sequence of (x, y) vertices.

    Returns:
        The rounded parts and their bounding box.

    Raises:
        ValueError: If there is no part, a part has fewer than 3 vertices, or a vertex
            is not finite.
    """
    if len(polygons) < 1:
        raise ValueError("A polygon needs at least 1 part.")
    rounded_parts = [_round_part(part=part) for part in polygons]
    xs = [x for part in rounded_parts for x, _ in part]
    ys = [y for part in rounded_parts for _, y in part]
    x = math.floor(min(xs))
    y = math.floor(min(ys))
    return ValidatedPolygons(
        polygons=rounded_parts,
        x=x,
        y=y,
        width=math.ceil(max(xs)) - x,
        height=math.ceil(max(ys)) - y,
    )


def _round_part(part: Sequence[Sequence[float]]) -> list[list[float]]:
    if len(part) < MIN_VERTICES_PER_PART:
        raise ValueError(f"Each polygon part needs at least {MIN_VERTICES_PER_PART} vertices.")
    rounded_part = []
    for x, y in part:
        if not (math.isfinite(x) and math.isfinite(y)):
            raise ValueError("Polygon vertices must be finite numbers.")
        rounded_part.append([round(x, COORDINATE_DECIMALS), round(y, COORDINATE_DECIMALS)])
    return rounded_part
