"""API view of an MCAP sequence's lidar and camera channels, read from the database."""

from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, Field

from lightly_studio.models.mcap_group_component_definition import (
    McapDataType,
    McapGroupComponentDefinitionView,
)
from lightly_studio.models.mcap_group_sequence import McapGroupSequenceInfoView
from lightly_studio.models.recording import RecordingFormat


class ChannelSummaryView(BaseModel):
    """One MCAP channel, as configured on the indexed sequence's GROUP collection."""

    channel_id: int = Field(description="The MCAP channel id, unique within the sequence.")
    group_component_name: str = Field(description="The Studio slot name, e.g. `front`.")
    group_component_index: int = Field(description="The slot's position among its siblings.")
    frame_id: str | None = Field(
        default=None,
        description="The id used to match this slot against calibration/transform data. "
        "`None` if the slot has none.",
    )
    first_keyframe_log_time_ns: int | None = Field(
        default=None,
        description="The earliest keyframe_log_time_ns for this channel, in nanoseconds. "
        "`None` if no ticks with a keyframe have been indexed yet.",
    )

    @classmethod
    def from_component(
        cls,
        component: McapGroupComponentDefinitionView,
        first_keyframe_log_time_ns: int | None = None,
    ) -> ChannelSummaryView:
        """Builds the API view of a channel from its MCAP group component definition."""
        return cls(
            channel_id=component.channel_id,
            group_component_name=component.group_component_name,
            group_component_index=component.group_component_index,
            frame_id=component.frame_id,
            first_keyframe_log_time_ns=first_keyframe_log_time_ns,
        )


class MCAPSequenceSummary(BaseModel):
    """Summary of the lidar and camera channels an indexed MCAP sequence is known to have.

    Built entirely from the database: the component slots an indexing script attached
    to the sequence. Does not open the sequence's file, so it is only available once
    a sequence has been indexed.
    """

    recording_id: UUID = Field(description="The MCAP sequence this summary describes.")
    format: RecordingFormat = Field(description="The sequence's file format.")
    start_log_time_ns: int | None = Field(
        description="The earliest log_time_ns across all indexed ticks, in nanoseconds. "
        "`None` if no ticks have been indexed yet."
    )
    start_timestamp_ns: int | None = Field(
        description="The earliest anchor-channel log time across all sequence slots, "
        "in nanoseconds. `None` if no slot has a timestamp."
    )
    lidar_channels: list[ChannelSummaryView] = Field(
        description="Point-cloud channels, e.g. lidar sweeps."
    )
    camera_channels: list[ChannelSummaryView] = Field(
        description="Image and video channels, e.g. compressed camera frames."
    )

    @classmethod
    def from_info(
        cls,
        info: McapGroupSequenceInfoView,
        start_log_time_ns: int | None,
        start_timestamp_ns: int | None,
        first_keyframe_log_time_ns_by_channel: dict[int, int] | None = None,
    ) -> MCAPSequenceSummary:
        """Builds the summary from a sequence's `McapGroupSequenceInfoView`.

        Args:
            info: The sequence's recording and component schema, e.g. from
                `mcap_group_sequence_resolver.get_info`.
            start_log_time_ns: The earliest log time across all indexed ticks, or
                `None` if no ticks have been indexed yet.
            start_timestamp_ns: The earliest anchor-channel log time across all sequence
                slots, or `None` if no slot has a timestamp.
            first_keyframe_log_time_ns_by_channel: Mapping from channel_id to its
                earliest keyframe_log_time_ns, as returned by
                `mcap_resolver.get_first_keyframe_log_time_ns_by_channel`.
        """
        keyframe_map = first_keyframe_log_time_ns_by_channel or {}
        lidar_channels: list[ChannelSummaryView] = []
        camera_channels: list[ChannelSummaryView] = []

        for component in info.components:
            channel = ChannelSummaryView.from_component(
                component=component,
                first_keyframe_log_time_ns=keyframe_map.get(component.channel_id),
            )
            if component.mcap_data_type is McapDataType.POINT_CLOUD:
                lidar_channels.append(channel)
            elif component.mcap_data_type is McapDataType.VIDEO_FRAME:
                camera_channels.append(channel)

        return cls(
            recording_id=info.recording.recording_id,
            format=info.recording.format,
            start_log_time_ns=start_log_time_ns,
            start_timestamp_ns=start_timestamp_ns,
            lidar_channels=lidar_channels,
            camera_channels=camera_channels,
        )
