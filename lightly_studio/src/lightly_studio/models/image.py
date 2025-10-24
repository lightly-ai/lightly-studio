"""This module defines the User model for the application."""

from datetime import datetime, timezone
from typing import TYPE_CHECKING, List, Literal, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict
from pydantic import Field as PydanticField
from sqlalchemy.orm import Mapped
from sqlmodel import Field, Relationship, SQLModel

from lightly_studio.models.annotation.annotation_base import AnnotationView
from lightly_studio.models.caption import CaptionView

if TYPE_CHECKING:
    from lightly_studio.models.annotation.annotation_base import (
        AnnotationBaseTable,
    )
    from lightly_studio.models.metadata import (
        SampleMetadataView,
    )
    from lightly_studio.models.sample import SampleTable
else:
    AnnotationBaseTable = object
    SampleTable = object
    SampleMetadataView = object


class ImageBase(SQLModel):
    """Base class for the Image model."""

    """The name of the image file."""
    file_name: str

    """The width of the image in pixels."""
    width: int

    """The height of the image in pixels."""
    height: int

    """The dataset ID to which the sample belongs."""
    dataset_id: UUID = Field(default=None, foreign_key="dataset.dataset_id")

    """The dataset image path."""
    file_path_abs: str = Field(default=None, unique=True)


class ImageCreate(ImageBase):
    """Image class when inserting."""


class ImageTable(ImageBase, table=True):
    """This class defines the Image model."""

    __tablename__ = "image"
    sample_id: UUID = Field(foreign_key="sample.sample_id", primary_key=True)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), index=True)
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
    )
    annotations: Mapped[List["AnnotationBaseTable"]] = Relationship(
        back_populates="sample",
    )

    sample: Mapped["SampleTable"] = Relationship()


TagKind = Literal[
    "sample",
    "annotation",
]


class ImageView(SQLModel):
    """Image class when retrieving."""

    class ImageViewTag(SQLModel):
        """Tag view inside Image view."""

        tag_id: UUID
        name: str
        kind: TagKind
        created_at: datetime
        updated_at: datetime

    """The name of the image file."""
    file_name: str
    file_path_abs: str
    sample_id: UUID
    dataset_id: UUID
    annotations: List["AnnotationView"]
    width: int
    height: int

    # TODO(Michal, 10/2025): Add SampleView to ImageView, don't expose these fields directly.
    tags: List[ImageViewTag]
    metadata_dict: Optional["SampleMetadataView"] = None
    captions: List[CaptionView] = []


class ImageViewsWithCount(BaseModel):
    """Response model for counted images."""

    model_config = ConfigDict(populate_by_name=True)

    samples: List[ImageView] = PydanticField(..., alias="data")
    total_count: int
    next_cursor: Optional[int] = PydanticField(None, alias="nextCursor")
