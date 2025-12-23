"""This module contains the Tag model and related enumerations."""

from datetime import datetime, timezone
from typing import List, Literal, Optional
from uuid import UUID, uuid4

from sqlalchemy import UniqueConstraint
from sqlalchemy.orm import Mapped
from sqlmodel import Field, Relationship, SQLModel, String

from lightly_studio.models.annotation.annotation_base import (
    AnnotationBaseTable,
)
from lightly_studio.models.annotation.links import AnnotationTagLinkTable
from lightly_studio.models.sample import SampleTable, SampleTagLinkTable

# TagKind is the kind of tag we support.
TagKind = Literal[
    "sample",
    "annotation",
]


class TagBase(SQLModel):
    """Base class for the Tag model."""

    name: str
    description: Optional[str] = ""
    kind: TagKind = "sample"


class TagCreate(TagBase):
    """Tag model when creating."""

    collection_id: UUID


class TagCreateBody(TagBase):
    """Tag model when creating."""


class TagUpdate(TagBase):
    """Tag model when updating."""


class TagUpdateBody(TagBase):
    """Tag model when updating."""

    collection_id: Optional[UUID] = None


class TagView(TagBase):
    """Tag model when retrieving."""

    tag_id: UUID
    kind: TagKind
    created_at: datetime
    updated_at: datetime


class TagTable(TagBase, table=True):
    """This class defines the Tag model."""

    __tablename__ = "tag"
    # ensure there can only be one tag named "lightly_studio" per collection
    __table_args__ = (
        UniqueConstraint("collection_id", "kind", "name", name="unique_name_constraint"),
    )
    tag_id: UUID = Field(default_factory=uuid4, primary_key=True)
    collection_id: UUID
    kind: TagKind = Field(sa_type=String)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), index=True)
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
    )

    """The sample ids associated with the tag."""
    samples: Mapped[List["SampleTable"]] = Relationship(
        back_populates="tags",
        link_model=SampleTagLinkTable,
    )

    """The annotation ids associated with the tag (legacy bounding box)."""
    annotations: Mapped[List["AnnotationBaseTable"]] = Relationship(
        back_populates="tags",
        link_model=AnnotationTagLinkTable,
    )
