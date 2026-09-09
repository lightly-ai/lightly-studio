"""Reading an MCAP recording's index to find point-cloud frames.

A frame is located, never decoded, here: the browser decodes payloads itself after reading
byte ranges of the recording. This module only walks the recording's own index to say which
channels carry point clouds and which messages exist on them.
"""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass

from mcap.reader import McapReader
from mcap.records import Channel, Schema

from lightly_studio.core.mcap.create_mcap import CreateMcap

# ROS 2 publishes point clouds under either name, depending on the generator that produced
# the schema. Both are the same message layout.
POINT_CLOUD_SCHEMA_NAMES = frozenset({"sensor_msgs/msg/PointCloud2", "sensor_msgs/PointCloud2"})


@dataclass(frozen=True)
class PointCloudChannel:
    """A recording channel whose messages the browser can decode.

    Attributes:
        channel_id: The MCAP channel id, unique within the recording.
        topic: The channel's topic name.
        schema_name: The ROS message type on the channel.
        message_count: Messages on the channel, when the recording's statistics report it.
    """

    channel_id: int
    topic: str
    schema_name: str
    message_count: int | None


def find_point_cloud_channels(reader: McapReader) -> list[PointCloudChannel]:
    """Return the recording's ROS 2 CDR point-cloud channels, in channel id order.

    Args:
        reader: A reader over an indexed recording.

    Returns:
        One entry per supported channel. Empty when the recording has none.

    Raises:
        ValueError: The recording has no summary section, so its messages cannot be seeked
            to and neither the workspace nor this indexing can use it.
    """
    summary = reader.get_summary()
    if summary is None:
        raise ValueError(
            "The recording has no summary section, so its messages cannot be seeked to. "
            "Re-index it with a writer that writes a summary."
        )

    counts = summary.statistics.channel_message_counts if summary.statistics else {}
    return [
        PointCloudChannel(
            channel_id=channel.id,
            topic=channel.topic,
            schema_name=summary.schemas[channel.schema_id].name,
            message_count=counts.get(channel.id),
        )
        for channel in sorted(summary.channels.values(), key=lambda item: item.id)
        if _is_point_cloud(channel=channel, schema=summary.schemas.get(channel.schema_id))
    ]


def iter_point_cloud_frames(
    reader: McapReader, *, topic: str, limit: int | None = None
) -> Iterator[CreateMcap]:
    """Yield a locator sample per point-cloud message on a topic, in log time order.

    The sensor's own capture stamp lives inside the PointCloud2 header, which only a decoder
    reads. Publish time is the closest stamp available without decoding, so it stands in for
    the capture stamp that aligns channels.

    Args:
        reader: A reader over an indexed recording.
        topic: The topic to walk.
        limit: Stop after this many messages. None walks the whole topic, which on a long
            recording means tens of thousands of samples.

    Yields:
        A ``CreateMcap`` per message, ready to add to an MCAP collection.
    """
    for index, (_schema, _channel, message) in enumerate(reader.iter_messages(topics=[topic])):
        if limit is not None and index >= limit:
            return
        yield CreateMcap(
            channel_id=message.channel_id,
            log_time_ns=message.log_time,
            capture_timestamp_ns=message.publish_time,
        )


def _is_point_cloud(*, channel: Channel, schema: Schema | None) -> bool:
    """Whether a channel carries ROS 2 CDR point clouds."""
    return (
        channel.message_encoding == "cdr"
        and schema is not None
        and schema.encoding == "ros2msg"
        and schema.name in POINT_CLOUD_SCHEMA_NAMES
    )
