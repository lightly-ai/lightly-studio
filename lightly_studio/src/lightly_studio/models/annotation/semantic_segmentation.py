"""This module defines the semantic segmentation annotation model.

Semantic segmentation is a computer vision task that assigns a class label to
each pixel in an image. This module provides the data models for storing and
managing semantic segmentation annotations.
"""

from typing import TYPE_CHECKING, List
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


class SemanticSegmentationAnnotationTable(SQLModel, table=True):
    """Model used to define semantic segmentation annotation table."""

    __tablename__ = "semantic_segmentation_annotations"

    annotation_id: UUID = Field(
        default_factory=uuid4,
        primary_key=True,
        foreign_key="annotation_base.annotation_id",
    )

    segmentation_mask: List[int] = Field(sa_column=Column(ARRAY(Integer), nullable=True))

    annotation_base: Mapped["AnnotationBaseTable"] = Relationship(
        back_populates="semantic_segmentation_details"
    )


class SemanticSegmentationAnnotationView(SQLModel):
    """Response model for semantic segmentation annotation."""

    segmentation_mask: List[int]
