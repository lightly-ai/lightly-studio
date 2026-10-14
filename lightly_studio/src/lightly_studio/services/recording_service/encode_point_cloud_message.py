"""Encodes one decoded point-cloud message as an Arrow IPC stream."""

from __future__ import annotations

import logging
from collections.abc import Sequence
from uuid import UUID

import numpy as np
from numpy.typing import NDArray
from sqlmodel import Session

from lightly_studio.core.mcap import capture_time
from lightly_studio.core.mcap.errors import TransformNotFoundError
from lightly_studio.core.mcap.reader import McapFileReader
from lightly_studio.core.mcap.type_definitions import DecodedMessage, StaticTransform
from lightly_studio.services.recording_service import (
    load_dynamic_transforms,
    point_cloud_value,
    serialize_point_cloud,
    transform_to_target_frame,
)

logger = logging.getLogger(__name__)


def encode_point_cloud_message(  # noqa: PLR0913
    session: Session,
    reader: McapFileReader,
    recording_id: UUID,
    message: DecodedMessage,
    target_frame_id: str | None,
    static_transforms: Sequence[StaticTransform],
) -> bytes:
    """Maps the points of a message to the target frame and serializes them.

    The points are mapped with the static and dynamic transforms of the recording at
    the capture time of the message. If no chain of transforms connects the sensor
    frame to `target_frame_id`, the points stay in the sensor frame. The `frame_id`
    in the Arrow metadata tells the frame the points are in.

    Args:
        session: Database session used to load the dynamic transforms.
        reader: Reader of the recording's MCAP file.
        recording_id: Recording the message was read from.
        message: A decoded PointCloud2 message.
        target_frame_id: Coordinate frame to express the points in. ``None`` keeps
            the points in the sensor frame.
        static_transforms: The static transforms of the recording. Only used when
            the points are mapped.

    Returns:
        The points as an Arrow IPC stream.

    Raises:
        McapAccessError: If the message misses required fields or has no capture time.
    """
    source_frame_id = str(
        point_cloud_value.get_value(
            value=point_cloud_value.get_value(value=message.decoded_message, name="header"),
            name="frame_id",
        )
    )
    if target_frame_id is None or target_frame_id == source_frame_id:
        return _serialize(message=message, transform=None, frame_id=target_frame_id)

    # TODO(Horatiu, 09/2026): We already have the capture time but only send the log time.
    # Consider changing the API to also send the capture time, so that we can use it here.
    transform_timestamp_ns = (
        capture_time.from_decoded_message(message.decoded_message) or message.log_time_ns
    )
    try:
        transform = transform_to_target_frame.transform_to_target_frame(
            reader=reader,
            source_frame_id=source_frame_id,
            target_frame_id=target_frame_id,
            timestamp_ns=transform_timestamp_ns,
            static_transforms=list(static_transforms),
            dynamic_transforms=load_dynamic_transforms.load_dynamic_transforms_near(
                session=session,
                recording_id=recording_id,
                timestamp_ns=transform_timestamp_ns,
            ),
        )
    except TransformNotFoundError as exc:
        logger.warning(
            "Point cloud channel %s stays in frame '%s': %s",
            message.channel_id,
            source_frame_id,
            exc,
        )
        return _serialize(message=message, transform=None, frame_id=None)
    return _serialize(message=message, transform=transform, frame_id=target_frame_id)


def _serialize(
    message: DecodedMessage, transform: NDArray[np.float64] | None, frame_id: str | None
) -> bytes:
    """Serializes the points of a message with an optional transform."""
    return serialize_point_cloud.serialize_point_cloud(
        message=message.decoded_message,
        channel_id=message.channel_id,
        topic=message.topic,
        log_time_ns=message.log_time_ns,
        transform=transform,
        frame_id=frame_id,
    ).data
