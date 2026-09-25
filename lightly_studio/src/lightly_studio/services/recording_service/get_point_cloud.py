"""Read one point-cloud message from a recording."""

from __future__ import annotations

from uuid import UUID

from sqlmodel import Session

from lightly_studio.core.mcap.errors import ChannelNotFoundError, McapAccessError
from lightly_studio.core.mcap.topic_kind import TopicKind
from lightly_studio.resolvers import recording_resolver
from lightly_studio.services.recording_service import reader_cache, serialize_point_cloud
from lightly_studio.services.recording_service.point_cloud_types import PointCloudPayload


def get_point_cloud(
    session: Session,
    dataset_id: UUID,
    recording_id: UUID,
    channel_id: int,
    timestamp_ns: int,
) -> PointCloudPayload | None:
    """Return one decoded point-cloud message as an Arrow IPC stream.

    Args:
        session: Database session used to resolve the recording.
        dataset_id: Dataset the recording must belong to.
        recording_id: Recording to read the point cloud from.
        channel_id: Channel that carries the point-cloud messages.
        timestamp_ns: Log time of the message to read, in nanoseconds.

    Returns:
        The decoded point-cloud payload, or ``None`` when the recording is
        unknown, does not belong to ``dataset_id``, or has no message at
        ``timestamp_ns``.

    Raises:
        ChannelNotFoundError: If ``channel_id`` is not present in the recording.
        McapAccessError: If ``channel_id`` does not carry a point cloud.
    """
    recording = recording_resolver.get_by_id(session=session, recording_id=recording_id)
    if recording is None or recording.dataset_id != dataset_id:
        return None
    reader = reader_cache.get_cached_reader(uri=recording.uri)
    topic = next((topic for topic in reader.get_topics() if topic.channel_id == channel_id), None)
    if topic is None:
        raise ChannelNotFoundError(f"Channel {channel_id} was not found.")
    if topic.kind is not TopicKind.POINT_CLOUD:
        raise McapAccessError(f"Channel {channel_id} does not carry a point cloud.")
    message = reader.get_decoded_message_at(channel_id=channel_id, timestamp_ns=timestamp_ns)
    if message is None:
        return None
    return serialize_point_cloud.serialize_point_cloud(
        message=message.decoded_message,
        channel_id=channel_id,
        topic=topic.name,
        log_time_ns=message.log_time_ns,
    )
