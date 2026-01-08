"""This module defines the Video and VideoFrame model for the application."""

from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict
from pydantic import Field as PydanticField
from sqlalchemy.orm import Mapped
from sqlmodel import Field, Relationship, SQLModel

from lightly_studio.models.range import FloatRange, IntRange
from lightly_studio.models.sample import SampleTable, SampleView


class VideoBase(SQLModel):
    """Base class for the Video model."""

    """The width of the video in pixels."""
    width: int

    """The height of the video in pixels."""
    height: int

    """The duration of the video in seconds."""
    duration_s: Optional[float] = Field(default=None)

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
    frames: Mapped[List["VideoFrameTable"]] = Relationship(
        sa_relationship_kwargs={"lazy": "select"}, back_populates="video"
    )
    sample: Mapped["SampleTable"] = Relationship()


class VideoView(SQLModel):
    """Video class when retrieving."""

    width: int
    height: int
    duration_s: Optional[float] = None
    fps: float
    file_name: str
    file_path_abs: str
    sample_id: UUID
    sample: SampleView
    frame: Optional["FrameView"] = None
    similarity_score: Optional[float] = None


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

    """Presentation timestamp in the video's time_base and in seconds."""
    frame_timestamp_pts: int
    frame_timestamp_s: float

    """The video ID to which the video frame belongs."""
    parent_sample_id: UUID = Field(default=None, foreign_key="video.sample_id")

    """The rotation of the encoded frame in degrees.

    Valid values are 0, 90, 180, 270. This field is needed for video access with OpenCV
    which does not read rotation metadata correctly."""
    rotation_deg: int = 0


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
    frame_timestamp_s: float
    sample_id: UUID

    # Video metadata routed from parent video
    video: VideoView
    sample: "SampleView"


class FrameView(SQLModel):
    """VideoFrame class when retrieving."""

    frame_number: int
    frame_timestamp_s: float
    sample_id: UUID
    sample: SampleView


class VideoFrameViewsWithCount(BaseModel):
    """Response model for counted video frames."""

    model_config = ConfigDict(populate_by_name=True)

    samples: List[VideoFrameView] = PydanticField(..., alias="data")
    total_count: int
    next_cursor: Optional[int] = PydanticField(None, alias="nextCursor")


class VideoFieldsBoundsView(BaseModel):
    """Response model for the video fields bounds."""

    width: IntRange
    height: IntRange
    duration_s: FloatRange
    fps: FloatRange


class VideoFrameFieldsBoundsView(BaseModel):
    """Response model for the video frame fields bounds."""

    frame_number: IntRange
