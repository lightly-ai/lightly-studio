"""API views for MCAP sequence tick list and per-tick channel locators."""

from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, Field

from lightly_studio.models.mcap import McapTable


class TickView(BaseModel):
    """One group in a sequence, identified by its position and anchor timestamp."""

    seq_number: int = Field(description="Zero-based position of the tick in the sequence.")
    timestamp_ns: int | None = Field(
        description="Anchor log time of the tick, in nanoseconds. `None` if not set at index time."
    )


class TickListView(BaseModel):
    """Ordered list of ticks for an MCAP sequence."""

    ticks: list[TickView]


class TickChannelView(BaseModel):
    """MCAP seek locator for one component of a tick."""

    channel_id: int = Field(description="The MCAP channel id, unique within the recording.")
    log_time_ns: int = Field(description="Log time of the message, in nanoseconds.")
    keyframe_log_time_ns: int | None = Field(
        default=None,
        description=(
            "Log time of the keyframe to seek to before decoding. `None` for non-video channels."
        ),
    )

    @classmethod
    def from_mcap_table(cls, mcap: McapTable) -> TickChannelView:
        """Build from a McapTable row."""
        return cls(
            channel_id=mcap.channel_id,
            log_time_ns=mcap.log_time_ns,
            keyframe_log_time_ns=mcap.keyframe_log_time_ns,
        )


class TickDetailView(BaseModel):
    """One tick with its per-component MCAP locators."""

    recording_id: UUID = Field(description="The recording this tick belongs to.")
    seq_number: int = Field(description="Zero-based position of the tick in the sequence.")
    timestamp_ns: int | None = Field(description="Anchor log time of the tick, in nanoseconds.")
    channels: dict[str, TickChannelView] = Field(
        description="MCAP locators keyed by component name, e.g. `front` or `pcl_front`."
    )
