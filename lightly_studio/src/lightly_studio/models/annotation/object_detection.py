"""Object detection annotation models.

Object detection identifies and locates objects in images using bounding boxes.
"""

from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy.orm import Mapped
from sqlmodel import Field, Relationship, SQLModel

if TYPE_CHECKING:
    from lightly_studio.models.annotation.annotation_base import (
        AnnotationBaseTable,
    )
else:
    AnnotationBaseTable = object


class ObjectDetectionAnnotationTable(SQLModel, table=True):
    """Database table model for object detection annotations."""

    __tablename__ = "object_detection_annotation"

    sample_id: UUID = Field(
        default_factory=uuid4,
        primary_key=True,
        foreign_key="annotation_base.sample_id",
    )

    annotation_base: Mapped["AnnotationBaseTable"] = Relationship(
        back_populates="object_detection_details"
    )

    x: int
    y: int
    width: int
    height: int


class ObjectDetectionAnnotationView(SQLModel):
    """API response model for object detection annotations."""

    x: float
    y: float
    width: float
    height: float
