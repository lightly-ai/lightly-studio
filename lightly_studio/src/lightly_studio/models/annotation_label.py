"""This module defines the AnnotationLabel model for the application."""

from datetime import datetime, timezone
from typing import Annotated
from uuid import UUID, uuid4

from pydantic import StringConstraints
from sqlalchemy.orm import Mapped
from sqlmodel import Field, Relationship, SQLModel, UniqueConstraint

from lightly_studio.models.annotation.annotation_base import (
    AnnotationBaseTable,
)


class AnnotationLabelBase(SQLModel):
    """Base class for the AnnotationLabel model."""

    # The dataset the label belongs to.
    dataset_id: UUID = Field(foreign_key="dataset.dataset_id", index=True)

    annotation_label_name: str


class AnnotationLabelCreate(AnnotationLabelBase):
    """Model used when creating an annotation label."""


class AnnotationLabelView(AnnotationLabelBase):
    """Model used when retrieving an annotation label."""

    annotation_label_id: UUID


class AnnotationLabelWithCountView(AnnotationLabelView):
    """Model used when retrieving an annotation label with its annotation count."""

    created_at: str
    annotation_count: int


class AnnotationLabelBatchCreateRequest(SQLModel):
    """Model used when creating multiple annotation labels."""

    annotation_label_names: list[Annotated[str, StringConstraints(max_length=255)]]


class AnnotationLabelTable(AnnotationLabelBase, table=True):
    """This class defines the AnnotationLabel model."""

    __tablename__ = "annotation_label"
    # Ensure that the combination of annotation_label_name and dataset_id is unique.
    __table_args__ = (UniqueConstraint("annotation_label_name", "dataset_id"),)

    annotation_label_id: UUID = Field(default_factory=uuid4, primary_key=True)
    # TODO (Mihnea, 01/2026): change to datetime
    created_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        index=True,
    )
    annotations: Mapped[list["AnnotationBaseTable"]] = Relationship(
        back_populates="annotation_label",
    )
