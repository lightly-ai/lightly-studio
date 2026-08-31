"""This module defines the Mcap model for the application.

Stores seek keys into an ``.mcap`` file (channel id + log time, optionally a
keyframe log time for video). Decoding and range requests happen later from these
locator fields; no payload bytes, file path, or topic are stored here.
"""

from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

from sqlalchemy import BigInteger
from sqlalchemy.orm import Mapped
from sqlmodel import Field, Relationship, SQLModel

from lightly_studio.models.collection import SampleType
from lightly_studio.models.sample import SampleTable, SampleView


class McapBase(SQLModel):
    """Base class for the Mcap model."""

    """The MCAP channel id, unique within the source bag."""
    channel_id: int

    """The MCAP log time, in nanoseconds."""
    log_time_ns: int = Field(sa_type=BigInteger)

    """The sensor/header capture timestamp, in nanoseconds. Used for cross-channel sync."""
    capture_timestamp_ns: int = Field(sa_type=BigInteger)

    """Log time of the keyframe to seek to before decoding. Required for camera channels."""
    keyframe_log_time_ns: Optional[int] = Field(default=None, sa_type=BigInteger)

    """Optional point count. Only meaningful for lidar channels."""
    point_count: Optional[int] = Field(default=None)


class McapCreate(McapBase):
    """Mcap class when inserting."""


class McapTable(McapBase, table=True):
    """This class defines the Mcap model."""

    __tablename__ = "mcap"
    sample_id: UUID = Field(foreign_key="sample.sample_id", primary_key=True)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), index=True)
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
    )
    sample: Mapped["SampleTable"] = Relationship()


class McapView(SQLModel):
    """Mcap class when retrieving."""

    type: SampleType = SampleType.MCAP
    sample_id: UUID
    channel_id: int
    log_time_ns: int
    capture_timestamp_ns: int
    keyframe_log_time_ns: Optional[int] = None
    point_count: Optional[int] = None

    sample: SampleView

    @classmethod
    def from_mcap_table(cls, mcap: "McapTable") -> "McapView":
        """Convert a McapTable to a McapView.

        Args:
            mcap: The mcap row to convert.
        """
        return cls(
            sample_id=mcap.sample_id,
            channel_id=mcap.channel_id,
            log_time_ns=mcap.log_time_ns,
            capture_timestamp_ns=mcap.capture_timestamp_ns,
            keyframe_log_time_ns=mcap.keyframe_log_time_ns,
            point_count=mcap.point_count,
            sample=SampleView.model_validate(mcap.sample),
        )
