"""This module contains the Tag model and related enumerations."""

from datetime import datetime, timezone
from uuid import UUID, uuid4

from sqlalchemy import UniqueConstraint
from sqlalchemy.orm import Mapped
from sqlmodel import Field, Relationship, SQLModel

from lightly_studio.models.sample import SampleTable, SampleTagLinkTable

MAX_SAMPLE_IDS_PER_REQUEST = 1000


class TagBase(SQLModel):
    """Base class for the Tag model."""

    name: str


class TagCreate(TagBase):
    """Tag model when creating."""

    collection_id: UUID


class TagCreateBody(TagBase):
    """Tag model when creating."""


class TagRenameBody(SQLModel):
    """Request body for renaming a tag."""

    name: str


class TagSamplesBody(SQLModel):
    """Request body to add a tag to samples or to remove it from samples."""

    tag_name: str
    sample_ids: list[UUID] = Field(max_length=MAX_SAMPLE_IDS_PER_REQUEST)


class TagView(TagBase):
    """Tag model when retrieving."""

    tag_id: UUID
    created_at: datetime
    updated_at: datetime


class TagTable(TagBase, table=True):
    """This class defines the Tag model."""

    __tablename__ = "tag"
    # A tag name identifies a tag within a collection.
    __table_args__ = (UniqueConstraint("collection_id", "name", name="unique_name_constraint"),)
    tag_id: UUID = Field(default_factory=uuid4, primary_key=True)
    collection_id: UUID
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), index=True)
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
    )

    """The sample ids associated with the tag."""
    samples: Mapped[list["SampleTable"]] = Relationship(
        back_populates="tags",
        link_model=SampleTagLinkTable,
    )
