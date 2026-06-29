"""Polygon annotation models.

Polygon annotations represent closed shapes using ordered image-space points.
"""

from typing import TYPE_CHECKING, Optional
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


class PolygonAnnotationTable(SQLModel, table=True):
    """Database table model for polygon annotations."""

    __tablename__ = "polygon_annotation"

    sample_id: UUID = Field(
        default_factory=uuid4,
        primary_key=True,
        foreign_key="annotation_base.sample_id",
    )

    annotation_base: Mapped["AnnotationBaseTable"] = Relationship(
        back_populates="polygon_details"
    )

    points: list[list[float]] = Field(sa_column=Column(JSON, nullable=False))
    x: int
    y: int
    width: int
    height: int


class PolygonAnnotationView(SQLModel):
    """API response model for polygon annotations."""

    points: list[list[float]]
    x: Optional[int] = None
    y: Optional[int] = None
    width: Optional[int] = None
    height: Optional[int] = None
