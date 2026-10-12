"""Read one point-cloud message from a recording."""

from __future__ import annotations

import logging
import time
from uuid import UUID

from sqlmodel import Session

from lightly_studio.core.mcap import capture_time
from lightly_studio.core.mcap.errors import ChannelNotFoundError, McapAccessError
from lightly_studio.core.mcap.reader import range_cache
from lightly_studio.core.mcap.topic_kind import TopicKind
from lightly_studio.core.mcap.type_definitions import StaticTransform
from lightly_studio.resolvers import recording_resolver
from lightly_studio.services.recording_service import (
    load_dynamic_transforms,
    load_static_transforms,
    point_cloud_value,
    reader_cache,
    serialize_point_cloud,
    transform_to_target_frame,
)
from lightly_studio.services.recording_service.point_cloud_types import PointCloudPayload

logger = logging.getLogger(__name__)


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
            static and dynamic transforms of the recording at the capture time of the
            message. ``None`` keeps the points in the sensor frame.

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
    with reader_cache.borrow_reader(uri=recording.uri) as reader:
        topic = next(
            (topic for topic in reader.get_topics() if topic.channel_id == channel_id), None
        )
        if topic is None:
            raise ChannelNotFoundError(f"Channel {channel_id} was not found.")
        if topic.kind is not TopicKind.POINT_CLOUD:
            raise McapAccessError(f"Channel {channel_id} does not carry a point cloud.")
        range_cache.reset_read_account()
        read_started = time.perf_counter()
        message = reader.get_decoded_message_at(channel_id=channel_id, timestamp_ns=timestamp_ns)
        read_seconds = time.perf_counter() - read_started
        if message is None:
            _log_point_cloud(
                channel_id=channel_id,
                read_seconds=read_seconds,
                transform_seconds=0.0,
                encode_seconds=0.0,
            )
            return None
        source_frame_id = str(
            point_cloud_value.get_value(
                value=point_cloud_value.get_value(value=message.decoded_message, name="header"),
                name="frame_id",
            )
        )
        static_transforms: list[StaticTransform] = []
        dynamic_transforms: list[StaticTransform] | None = None
        transform_timestamp_ns = message.log_time_ns
        if target_frame_id is not None and target_frame_id != source_frame_id:
            static_transforms = load_static_transforms.load_static_transforms(
                session=session, recording_id=recording_id
            )
            # TODO(Horatiu, 09/2026): We already have the capture time but only send the log time.
            # Consider changing the API to also send the capture time, so that we can use it here.
            transform_timestamp_ns = (
                capture_time.from_decoded_message(message.decoded_message) or message.log_time_ns
            )
            dynamic_transforms = load_dynamic_transforms.load_dynamic_transforms_near(
                session=session,
                recording_id=recording_id,
                timestamp_ns=transform_timestamp_ns,
            )
        transform_started = time.perf_counter()
        transform = transform_to_target_frame.transform_to_target_frame(
            reader=reader,
            source_frame_id=source_frame_id,
            target_frame_id=target_frame_id,
            timestamp_ns=transform_timestamp_ns,
            static_transforms=static_transforms,
            dynamic_transforms=dynamic_transforms,
        )
        transform_seconds = time.perf_counter() - transform_started
        encode_started = time.perf_counter()
        payload = serialize_point_cloud.serialize_point_cloud(
            message=message.decoded_message,
            channel_id=channel_id,
            topic=topic.name,
            log_time_ns=message.log_time_ns,
            transform=transform,
            frame_id=target_frame_id,
        )
        _log_point_cloud(
            channel_id=channel_id,
            read_seconds=read_seconds,
            transform_seconds=transform_seconds,
            encode_seconds=time.perf_counter() - encode_started,
        )
        return payload


def _log_point_cloud(
    channel_id: int, read_seconds: float, transform_seconds: float, encode_seconds: float
) -> None:
    """Logs how a point cloud split its time between reading, transforming, and encoding."""
    logger.info(
        "Point cloud channel %s: read %.0f ms (%s), transform %.0f ms, encode %.0f ms.",
        channel_id,
        read_seconds * 1000,
        range_cache.describe_reads(),
        transform_seconds * 1000,
        encode_seconds * 1000,
    )
