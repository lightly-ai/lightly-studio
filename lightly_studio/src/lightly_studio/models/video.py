"""This module defines the VideoFrame model for the application."""

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
    from lightly_studio.models.metadata import (
        SampleMetadataView,
    )
    from lightly_studio.models.sample import SampleTable, SampleView
else:
    AnnotationBaseTable = object
    SampleTable = object
    SampleMetadataView = object


# VideoFrame

class VideoFrameBase(SQLModel):
    """Base class for the VideoFrame model."""

    """The frame number of the video frame."""
    frame_number: int

    """The timestamp of the video frame."""
    frame_timestamp: int

    """The video ID to which the video frame belongs."""
    video_sample_id: UUID = Field(default=None, foreign_key="sample.sample_id")


class VideoFrameCreate(VideoFrameBase):
    """VideoFrame class when inserting."""


class VideoFrameTable(VideoFrameBase, table=True):
    """This class defines the VideoFrame model."""

    __tablename__ = "video_frame"
    sample_id: UUID = Field(foreign_key="sample.sample_id", primary_key=True)
    annotations: Mapped[List["AnnotationBaseTable"]] = Relationship(
        back_populates="sample",
    )

    sample: Mapped["SampleTable"] = Relationship()
    video: Mapped["VideoTable"] = Relationship(back_populates="frames")


class VideoFrameView(SQLModel):
    """VideoFrame class when retrieving."""

    class VideoFrameViewVideo(SQLModel):
        """Video view inside VideoFrame view."""
        file_name: str
        file_path_abs: str
        sample_id: UUID
        width: int
        height: int
        duration: float
        fps: float

    """The frame number of the video frame."""
    frame_number: int
    frame_timestamp: int
    sample_id: UUID
    video_sample_id: UUID

    # Video metadata routed from parent video
    video: VideoFrameViewVideo
    sample: SampleView


class VideoFrameViewsWithCount(BaseModel):
    """Response model for counted video frames."""

    model_config = ConfigDict(populate_by_name=True)

    samples: List[VideoFrameView] = PydanticField(..., alias="data")
    total_count: int
    next_cursor: Optional[int] = PydanticField(None, alias="nextCursor")



# Video

class VideoBase(SQLModel):
    """Base class for the Video model."""

    """The width of the video."""
    width: int

    """The height of the video."""
    height: int

    """The curation of the video."""
    duration: float

    """The fps of the video."""
    fps: float

    """The file name of the video."""
    file_name: str

    """The path of the video."""
    file_path_abs: str = Field(default=None)

    """The dataset ID to which the video belongs."""
    dataset_id: UUID = Field(default=None, foreign_key="dataset.dataset_id")


class VideoCreate(VideoBase):
    """Video class when inserting."""


class VideoTable(VideoBase, table=True):
    """This class defines the Video ORM table."""

    __tablename__ = "video"
    sample_id: UUID = Field(foreign_key="sample.sample_id", primary_key=True)
    frames: Mapped[List["VideoFrameTable"]] = Relationship(back_populates="video")
    sample: Mapped["SampleTable"] = Relationship()


class VideoView(VideoBase):
    """Video class when retrieving."""

    file_name: str
    file_path_abs: str
    sample_id: UUID
    sample: SampleView
    frames: List["VideoFrameView"] = []
    width: int
    height: int
    duration: float
    fps: float


class VideoViewsWithCount(BaseModel):
    """Response model for counted videos."""

    model_config = ConfigDict(populate_by_name=True)

    samples: List[VideoView] = PydanticField(..., alias="data")
    total_count: int
    next_cursor: Optional[int] = PydanticField(None, alias="nextCursor")
