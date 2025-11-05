"""This module defines the Video and VideoFrame model for the application."""

from typing import TYPE_CHECKING, List, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict
from pydantic import Field as PydanticField
from sqlalchemy.orm import Mapped
from sqlmodel import Field, Relationship, SQLModel

if TYPE_CHECKING:
    from lightly_studio.models.annotation.annotation_base import (
        AnnotationBaseTable,
    )
    from lightly_studio.models.sample import SampleTable, SampleView

else:
    AnnotationBaseTable = object
    SampleTable = object
    SampleView = object


class VideoBase(SQLModel):
    """Base class for the Video model."""

    """The width of the video in pixels."""
    width: int

    """The height of the video in pixels."""
    height: int

    """The duration of the video in seconds."""
    duration: float

    """The fps of the video."""
    fps: float

    """The file name of the video."""
    file_name: str

    """The path of the video."""
    file_path_abs: str = Field(default=None)


class VideoCreate(VideoBase):
    """Video class when inserting."""


class VideoTable(VideoBase, table=True):
    """This class defines the Video ORM table."""

    __tablename__ = "video"
    sample_id: UUID = Field(foreign_key="sample.sample_id", primary_key=True)
    frames: Mapped[List["VideoFrameTable"]] = Relationship(back_populates="video")
    sample: Mapped["SampleTable"] = Relationship()


class VideoView(SQLModel):
    """Video class when retrieving."""

    width: int
    height: int
    duration: float
    fps: float
    file_name: str
    file_path_abs: str
    sample_id: UUID
    sample: SampleView


class VideoViewsWithCount(BaseModel):
    """Response model for counted videos."""

    model_config = ConfigDict(populate_by_name=True)

    samples: List[VideoView] = PydanticField(..., alias="data")
    total_count: int
    next_cursor: Optional[int] = PydanticField(None, alias="nextCursor")


class VideoFrameBase(SQLModel):
    """Base class for the VideoFrame model."""

    """The frame number of the video frame."""
    frame_number: int

    """The timestamp of the video frame."""
    frame_timestamp: float

    """The video ID to which the video frame belongs."""
    video_sample_id: UUID = Field(default=None, foreign_key="video.sample_id")


class VideoFrameCreate(VideoFrameBase):
    """VideoFrame class when inserting."""


class VideoFrameTable(VideoFrameBase, table=True):
    """This class defines the VideoFrame model."""

    __tablename__ = "video_frame"
    sample_id: UUID = Field(foreign_key="sample.sample_id", primary_key=True)

    sample: Mapped["SampleTable"] = Relationship()
    video: Mapped["VideoTable"] = Relationship(back_populates="frames")


class VideoFrameView(SQLModel):
    """VideoFrame class when retrieving."""

    frame_number: int
    frame_timestamp: int
    sample_id: UUID
    video_sample_id: UUID

    # Video metadata routed from parent video
    video: VideoView
    sample: SampleView


class VideoFrameViewsWithCount(BaseModel):
    """Response model for counted video frames."""

    model_config = ConfigDict(populate_by_name=True)

    samples: List[VideoFrameView] = PydanticField(..., alias="data")
    total_count: int
    next_cursor: Optional[int] = PydanticField(None, alias="nextCursor")
