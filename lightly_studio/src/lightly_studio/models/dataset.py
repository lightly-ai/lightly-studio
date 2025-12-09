"""This module contains the Dataset model and related enumerations."""

from datetime import datetime, timezone
from enum import Enum
from typing import List, Optional
from uuid import UUID, uuid4

from sqlmodel import Field, Relationship, SQLModel


class SampleType(str, Enum):
    """The type of samples in the dataset."""

    VIDEO = "video"
    VIDEO_FRAME = "video_frame"
    IMAGE = "image"
    ANNOTATION = "annotation"
    CAPTION = "caption"


class DatasetBase(SQLModel):
    """Base class for the Dataset model."""

    name: str = Field(unique=True, index=True)
    parent_dataset_id: Optional[UUID] = Field(default=None, foreign_key="dataset.dataset_id")
    sample_type: SampleType


class DatasetCreate(DatasetBase):
    """Dataset class when inserting."""


class DatasetView(DatasetBase):
    """Dataset class when retrieving."""

    dataset_id: UUID
    created_at: datetime
    updated_at: datetime
    children: List["DatasetView"] = []


class DatasetViewWithCount(DatasetView):
    """Dataset view with total sample count."""

    total_sample_count: int


class DatasetOverviewView(SQLModel):
    """Dataset view for dashboard display."""

    dataset_id: UUID
    name: str
    sample_type: SampleType
    created_at: datetime
    total_sample_count: int


class DatasetTable(DatasetBase, table=True):
    """This class defines the Dataset model."""

    __tablename__ = "dataset"
    dataset_id: UUID = Field(default_factory=uuid4, primary_key=True)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), index=True)
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    parent: Optional["DatasetTable"] = Relationship(
        back_populates="children",
        sa_relationship_kwargs={"remote_side": "DatasetTable.dataset_id"},
    )
    children: List["DatasetTable"] = Relationship(back_populates="parent")
