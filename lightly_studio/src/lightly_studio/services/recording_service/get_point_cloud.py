"""Read one point-cloud message from a recording."""

from __future__ import annotations

from collections.abc import Sequence
from uuid import UUID

import numpy as np
from numpy.typing import NDArray
from sqlmodel import Session

from lightly_studio.core.mcap.errors import ChannelNotFoundError, McapAccessError
from lightly_studio.core.mcap.reader import McapFileReader
from lightly_studio.core.mcap.topic_kind import TopicKind
from lightly_studio.core.mcap.type_definitions import StaticTransform
from lightly_studio.resolvers import recording_resolver
from lightly_studio.services.recording_service import (
    load_static_transforms,
    point_cloud_value,
    reader_cache,
    serialize_point_cloud,
)
from lightly_studio.services.recording_service.point_cloud_types import PointCloudPayload


def get_point_cloud(  # noqa: PLR0913
    session: Session,
    dataset_id: UUID,
    recording_id: UUID,
    channel_id: int,
    timestamp_ns: int,
    target_frame_id: str | None = None,
) -> PointCloudPayload | None:
    """Return one decoded point-cloud message as an Arrow IPC stream.

    Args:
        session: Database session used to resolve the recording.
        dataset_id: Dataset the recording must belong to.
        recording_id: Recording to read the point cloud from.
        channel_id: Channel that carries the point-cloud messages.
        timestamp_ns: Log time of the message to read, in nanoseconds.
        target_frame_id: Coordinate frame to express the points in, e.g. the world
            frame. The points are mapped from the frame in the message header with the
            static and dynamic transforms of the recording. ``None`` keeps the points
            in the sensor frame.

    Returns:
        The decoded point-cloud payload, or ``None`` when the recording is
        unknown, does not belong to ``dataset_id``, or has no message at
        ``timestamp_ns``.

    Raises:
        ChannelNotFoundError: If ``channel_id`` is not present in the recording.
        McapAccessError: If ``channel_id`` does not carry a point cloud, if the
            message has no capture time, or if no chain of transforms connects the
            sensor frame to ``target_frame_id``.
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
    source_frame_id = str(
        point_cloud_value.get_value(
            value=point_cloud_value.get_value(value=message.decoded_message, name="header"),
            name="frame_id",
        )
    )
    static_transforms: list[StaticTransform] = []
    if target_frame_id is not None and target_frame_id != source_frame_id:
        static_transforms = load_static_transforms.load_static_transforms(
            session=session, recording_id=recording_id
        )
    transform = _transform_to_target_frame(
        reader=reader,
        source_frame_id=source_frame_id,
        target_frame_id=target_frame_id,
        timestamp_ns=timestamp_ns,
        static_transforms=static_transforms,
    )
    return serialize_point_cloud.serialize_point_cloud(
        message=message.decoded_message,
        channel_id=channel_id,
        topic=topic.name,
        log_time_ns=message.log_time_ns,
        transform=transform,
        frame_id=target_frame_id,
    )


def _transform_to_target_frame(
    reader: McapFileReader,
    source_frame_id: str,
    target_frame_id: str | None,
    timestamp_ns: int,
    static_transforms: Sequence[StaticTransform],
) -> NDArray[np.float64] | None:
    """Return the transform from the sensor frame to the target frame at a time.

    Returns `None` if the points stay in the sensor frame, so a recording without
    transforms can still serve points in their own frame. The static edges come from
    the database. The dynamic edges are read from the recording at `timestamp_ns`.
    """
    if target_frame_id is None or target_frame_id == source_frame_id:
        return None
    return reader.get_transform_at(
        parent_frame_id=target_frame_id,
        child_frame_id=source_frame_id,
        timestamp_ns=timestamp_ns,
        static_transforms=static_transforms,
    )
