"""This module contains the Collection model and related enumerations."""

from datetime import datetime, timezone
from enum import Enum
from typing import List, Optional
from uuid import UUID, uuid4

from sqlmodel import Field, Relationship, SQLModel


class SampleType(str, Enum):
    """The type of samples in the collection."""

    VIDEO = "video"
    VIDEO_FRAME = "video_frame"
    IMAGE = "image"
    ANNOTATION = "annotation"
    CAPTION = "caption"
    GROUP = "group"


class CollectionBase(SQLModel):
    """Base class for the Collection model."""

    name: str = Field(unique=True, index=True)
    parent_collection_id: Optional[UUID] = Field(
        default=None, foreign_key="collection.collection_id"
    )
    sample_type: SampleType

    # Group-specific fields
    group_component_name: Optional[str] = None
    group_component_index: Optional[int] = None


class CollectionCreate(CollectionBase):
    """Collection class when inserting."""


class CollectionView(CollectionBase):
    """Collection class when retrieving."""

    collection_id: UUID
    created_at: datetime
    updated_at: datetime
    children: List["CollectionView"] = []


class CollectionViewWithCount(CollectionView):
    """Collection view with total sample count."""

    total_sample_count: int


class CollectionOverviewView(SQLModel):
    """Collection view for dashboard display."""

    collection_id: UUID
    name: str
    sample_type: SampleType
    created_at: datetime
    total_sample_count: int


class CollectionTable(CollectionBase, table=True):
    """This class defines the Collection model."""

    __tablename__ = "collection"
    collection_id: UUID = Field(default_factory=uuid4, primary_key=True)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), index=True)
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    parent: Optional["CollectionTable"] = Relationship(
        back_populates="children",
        sa_relationship_kwargs={"remote_side": "CollectionTable.collection_id"},
    )
    children: List["CollectionTable"] = Relationship(
        back_populates="parent",
        sa_relationship_kwargs={"lazy": "select"},
    )
