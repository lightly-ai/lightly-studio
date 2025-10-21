"""Instance segmentation annotation models.

Instance segmentation combines object detection and semantic segmentation,
identifying objects and providing pixel-level masks for each instance.
"""

from typing import TYPE_CHECKING, List, Optional
from uuid import UUID, uuid4

from sqlalchemy import ARRAY, Column, Integer
from sqlalchemy.orm import Mapped
from sqlmodel import Field, Relationship, SQLModel

if TYPE_CHECKING:
    from lightly_studio.models.annotation.annotation_base import (
        AnnotationBaseTable,
    )
else:
    AnnotationBaseTable = object


class InstanceSegmentationAnnotationTable(SQLModel, table=True):
    """Database table model for instance segmentation annotations."""

    __tablename__ = "instance_segmentation_annotations"

    annotation_id: UUID = Field(
        default_factory=uuid4,
        primary_key=True,
        foreign_key="annotation_base.annotation_id",
    )

    annotation_base: Mapped["AnnotationBaseTable"] = Relationship(
        back_populates="instance_segmentation_details"
    )

    x: int
    y: int
    width: int
    height: int
    # TODO(Kondrat 06/2025): We need to fix logic in the loader,
    # because it shouldn't be optional.
    # lightly_studio/dataset/loader.py#L148
    segmentation_mask: Optional[List[int]] = Field(
        default=None, sa_column=Column(ARRAY(Integer), nullable=True)
    )


class InstanceSegmentationAnnotationView(SQLModel):
    """API response model for instance segmentation annotations."""

    x: int
    y: int
    width: int
    height: int
    segmentation_mask: Optional[List[int]] = None
