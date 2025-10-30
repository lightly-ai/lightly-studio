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
    # TODO: Uncomment when video model is created
    # from lightly_studio.models.video import VideoTable
else:
    AnnotationBaseTable = object
    SampleTable = object
    SampleMetadataView = object
    VideoTable = object


class VideoFrameBase(SQLModel):
    """Base class for the VideoFrame model."""

    """The frame number of the video frame."""
    frame_number: int

    """The timestamp of the video frame."""
    frame_timestamp: int

    """The video ID to which the video frame belongs."""
    video_id: UUID = Field(default=None, foreign_key="video.video_id")


class VideoFrameCreate(VideoFrameBase):
    """VideoFrame class when inserting."""


class VideoFrameTable(VideoFrameBase, table=True):
    """This class defines the VideoFrame model."""

    __tablename__ = "video_frame"
    sample_id: UUID = Field(foreign_key="sample.sample_id", primary_key=True)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), index=True)
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
    )
    annotations: Mapped[List["AnnotationBaseTable"]] = Relationship(
        back_populates="sample",
    )

    sample: Mapped["SampleTable"] = Relationship()
    # TODO: Uncomment when video model is created
    # video: Mapped["VideoTable"] = Relationship(back_populates="frames")


TagKind = Literal[
    "sample",
    "annotation",
]


class VideoFrameView(SQLModel):
    """VideoFrame class when retrieving."""

    class VideoFrameViewTag(SQLModel):
        """Tag view inside VideoFrame view."""

        tag_id: UUID
        name: str
        kind: TagKind
        created_at: datetime
        updated_at: datetime

    """The frame number of the video frame."""
    frame_number: int
    frame_timestamp: int
    sample_id: UUID
    video_id: UUID
    annotations: List["AnnotationView"]

    # Video metadata routed from parent video
    # TODO(Jonas, 10/2025): resolve this more nicely.
    width: Optional[int] = None
    height: Optional[int] = None
    duration: Optional[float] = None
    fps: Optional[float] = None

    # TODO(Michal, 10/2025): Add SampleView to VideoFrameView, don't expose these fields directly.
    tags: List[VideoFrameViewTag]
    metadata_dict: Optional["SampleMetadataView"] = None
    captions: List[CaptionView] = []


class VideoFrameViewsWithCount(BaseModel):
    """Response model for counted video frames."""

    model_config = ConfigDict(populate_by_name=True)

    samples: List[VideoFrameView] = PydanticField(..., alias="data")
    total_count: int
    next_cursor: Optional[int] = PydanticField(None, alias="nextCursor")
