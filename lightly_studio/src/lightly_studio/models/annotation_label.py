"""This module defines the AnnotationLabel model for the application."""

from datetime import datetime, timezone
from uuid import UUID, uuid4

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
    color: str | None = None
    alpha: float | None = None


class AnnotationLabelWithCountView(AnnotationLabelView):
    """Model used when retrieving an annotation label with its number of annotations."""

    annotation_count: int


class AnnotationLabelTable(AnnotationLabelBase, table=True):
    """This class defines the AnnotationLabel model."""

    __tablename__ = "annotation_label"
    # The combination of annotation_label_name and dataset_id is unique. The resolvers check
    # this. Only PostgreSQL also has the constraint: DuckDB cannot update a column with an
    # index while a foreign key references the row, so a rename would fail.
    __table_args__ = (
        UniqueConstraint("annotation_label_name", "dataset_id").ddl_if(dialect="postgresql"),
    )

    annotation_label_id: UUID = Field(default_factory=uuid4, primary_key=True)
    # TODO (Mihnea, 01/2026): change to datetime
    created_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        index=True,
    )
    # Custom display color as "#rrggbb", and its opacity in [0, 1]. Null means the default color.
    color: str | None = None
    alpha: float | None = None
    annotations: Mapped[list["AnnotationBaseTable"]] = Relationship(
        back_populates="annotation_label",
    )
