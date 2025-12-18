"""This module defines the AnnotationLabel model for the application."""

from datetime import datetime, timezone
from typing import TYPE_CHECKING, List
from uuid import UUID, uuid4

from sqlalchemy import UniqueConstraint
from sqlalchemy.orm import Mapped
from sqlmodel import Field, Relationship, SQLModel

if TYPE_CHECKING:
    from lightly_studio.models.annotation.annotation_base import (
        AnnotationBaseTable,
    )

else:
    AnnotationBaseTable = object


class AnnotationLabelBase(SQLModel):
    """Base class for the AnnotationLabel model."""

    annotation_label_name: str

    # The root dataset the label belongs to.
    root_dataset_id: UUID = Field(foreign_key="dataset.dataset_id")


class AnnotationLabelCreate(AnnotationLabelBase):
    """Model used when creating an annotation label."""


class AnnotationLabelView(AnnotationLabelBase):
    """Model used when retrieving an annotation label."""

    annotation_label_id: UUID


class AnnotationLabelTable(AnnotationLabelBase, table=True):
    """This class defines the AnnotationLabel model."""

    __tablename__ = "annotation_label"
    # Ensure that the combination of annotation_label_name and root_dataset_id is unique.
    __table_args__ = (
        UniqueConstraint("annotation_label_name", "root_dataset_id"),
    )

    annotation_label_id: UUID = Field(default_factory=uuid4, primary_key=True)
    created_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        index=True,
    )
    annotations: Mapped[List["AnnotationBaseTable"]] = Relationship(
        back_populates="annotation_label",
    )
