"""This module defines the Sample model for the application."""

from datetime import datetime, timezone
from typing import TYPE_CHECKING, List, Optional
from uuid import UUID, uuid4

from sqlalchemy.orm import Mapped
from sqlmodel import Field, Relationship, SQLModel

if TYPE_CHECKING:
    from lightly_studio.models.tag import TagTable
else:
    TagTable = object


class SampleTagLinkTable(SQLModel, table=True):
    """Model to define links between Sample and Tag Many-to-Many."""

    sample_id: Optional[UUID] = Field(
        default=None, foreign_key="sample.sample_id", primary_key=True
    )
    tag_id: Optional[UUID] = Field(default=None, foreign_key="tag.tag_id", primary_key=True)


class SampleBase(SQLModel):
    """Base class for the Sample model."""

    """The dataset ID to which the sample belongs."""
    dataset_id: Optional[UUID] = Field(default=None, foreign_key="dataset.dataset_id")


class SampleCreate(SampleBase):
    """Sample class when inserting."""


class SampleTable(SampleBase, table=True):
    """This class defines the Sample model."""

    __tablename__ = "sample"
    sample_id: UUID = Field(default_factory=uuid4, primary_key=True)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), index=True)
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
    )

    tags: Mapped[List["TagTable"]] = Relationship(
        back_populates="samples", link_model=SampleTagLinkTable
    )


class SampleView(SampleBase):
    """This class defines the Sample view model."""

    sample_id: UUID
    created_at: datetime
    updated_at: datetime

    tags: List["TagTable"] = []
