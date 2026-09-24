"""API views for MCAP sequence tick list and per-tick channel locators."""

from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, Field

from lightly_studio.models.mcap import McapTable


class TickView(BaseModel):
    """One group in a sequence, identified by its position and capture timestamp."""

    seq_number: int = Field(description="Zero-based position of the tick in the sequence.")
    timestamp_ns: int | None = Field(
        description=(
            "Capture time of the tick's sync component, in nanoseconds. "
            "`None` if not set at index time."
        )
    )


class TickListView(BaseModel):
    """Ordered list of ticks for an MCAP sequence."""

    ticks: list[TickView]


class TickChannelView(BaseModel):
    """MCAP seek locator for one component of a tick."""

    channel_id: int = Field(description="The MCAP channel id, unique within the recording.")
    group_component_name: str = Field(
        description="Component name of the channel, e.g. `front` or `pcl_front`."
    )
    # Nanosecond log times exceed 2**53, so they are serialized as strings to survive a
    # round-trip through a JavaScript `number` (see McapGroupSequence.keyframe_log_time_ns).
    log_time_ns: str = Field(description="Log time of the message, in nanoseconds.")
    keyframe_log_time_ns: str | None = Field(
        default=None,
        description=(
            "Log time of the keyframe to seek to before decoding. `None` for non-video channels."
        ),
    )

    @classmethod
    def from_mcap_table(cls, mcap: McapTable, group_component_name: str) -> TickChannelView:
        """Build from a McapTable row and its component name."""
        return cls(
            channel_id=mcap.channel_id,
            group_component_name=group_component_name,
            log_time_ns=str(mcap.log_time_ns),
            keyframe_log_time_ns=(
                None if mcap.keyframe_log_time_ns is None else str(mcap.keyframe_log_time_ns)
            ),
        )


class TickDetailView(BaseModel):
    """One tick with its per-component MCAP locators."""

    recording_id: UUID = Field(description="The recording this tick belongs to.")
    seq_number: int = Field(description="Zero-based position of the tick in the sequence.")
    timestamp_ns: int | None = Field(
        description="Capture time of the tick's sync component, in nanoseconds."
    )
    channels: dict[str, TickChannelView] = Field(
        description="MCAP locators keyed by component name, e.g. `front` or `pcl_front`."
    )
