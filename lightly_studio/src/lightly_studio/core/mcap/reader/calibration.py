"""Reads camera intrinsics and transforms from an open MCAP file."""

from __future__ import annotations

import logging
from collections.abc import Iterable
from typing import Any

from mcap.exceptions import DecoderNotFoundError
from mcap.reader import McapReader
from mcap.records import Channel, Message, Schema

from lightly_studio.core.mcap import camera_info, transforms
from lightly_studio.core.mcap.errors import McapAccessError
from lightly_studio.core.mcap.reader.session import ChannelDecoder
from lightly_studio.core.mcap.type_definitions import CameraIntrinsics, StaticTransform

logger = logging.getLogger(__name__)

STATIC_TRANSFORM_TOPIC = "/tf_static"
DYNAMIC_TRANSFORM_TOPIC = "/tf"

# Dynamic transforms captured in this window before and after the requested time are
# used. The window holds a message of every transform published at 10 Hz or faster.
DYNAMIC_TRANSFORM_WINDOW_NS = 100_000_000


def read_intrinsic(messages: Iterable[tuple[int, Any]], topic: str) -> CameraIntrinsics:
    """Reads the camera intrinsics from the first message on a topic.

    Args:
        messages: The decoded messages of the topic, as log time and payload.
        topic: The camera info topic, used when the topic has no message.

    Returns:
        The intrinsics of the first message.

    Raises:
        McapAccessError: If the topic has no message, if its messages do not hold
            camera intrinsics, or if its messages cannot be decoded.
    """
    for _, decoded_message in messages:
        return camera_info.from_decoded_message(decoded_message)
    raise McapAccessError(f"Topic '{topic}' has no message to read camera intrinsics from.")


def read_static_transforms(messages: Iterable[tuple[int, Any]]) -> list[StaticTransform]:
    """Reads all transforms published on a topic.

    Args:
        messages: The decoded messages of the topic, as log time and payload.

    Returns:
        Every transform in those messages.

    Raises:
        McapAccessError: If a message on the topic cannot be decoded.
    """
    static_transforms: list[StaticTransform] = []
    for log_time_ns, decoded_message in messages:
        static_transforms.extend(
            transforms.from_decoded_message(decoded_message, log_time_ns=log_time_ns)
        )
    return static_transforms


def read_transforms(
    mcap_reader: McapReader,
    decoder: ChannelDecoder,
    path: str,
    topic: str,
) -> list[StaticTransform]:
    """Reads the transforms of every message on a topic, skipping unreadable messages.

    Args:
        mcap_reader: The seeking reader of the open file.
        decoder: Decodes a payload, or skips a message that cannot be decoded.
        path: The path or URI of the MCAP file, used in skip warnings.
        topic: The topic to read. The topic is in the file.

    Returns:
        One transform per edge in the topic. A message that cannot be decoded, or
        holds no transform, is skipped.
    """
    return [
        transform
        for schema, channel, message in mcap_reader.iter_messages(topics=[topic])
        for transform in transforms_of_message(
            decoder=decoder, path=path, schema=schema, channel=channel, message=message
        )
    ]


def dynamic_transforms_near(
    mcap_reader: McapReader,
    path: str,
    topic: str,
    timestamp_ns: int,
    topic_in_file: bool,
) -> list[StaticTransform]:
    """Returns, per child frame, the transform captured closest to a time.

    Only the transforms captured within `DYNAMIC_TRANSFORM_WINDOW_NS` of the time are
    used. Returns none if the topic is not in the file.

    Args:
        mcap_reader: The seeking reader of the open file.
        path: The path or URI of the MCAP file, used in error messages.
        topic: The topic the dynamic transforms are published on.
        timestamp_ns: The capture time to look up, in nanoseconds, e.g. the
            `header.stamp` of a point cloud.
        topic_in_file: Whether the topic is in the file.

    Returns:
        The transform captured closest to `timestamp_ns`, per child frame.

    Raises:
        McapAccessError: If a message on the topic cannot be decoded.
    """
    if not topic_in_file:
        return []
    edges = _read_dynamic_edges(
        mcap_reader=mcap_reader,
        path=path,
        topic=topic,
        start_ns=max(timestamp_ns - DYNAMIC_TRANSFORM_WINDOW_NS, 0),
        end_ns=timestamp_ns + DYNAMIC_TRANSFORM_WINDOW_NS + 1,
    )
    return closest_dynamic_transforms(edges=edges, timestamp_ns=timestamp_ns)


def closest_dynamic_transforms(
    edges: Iterable[StaticTransform], timestamp_ns: int
) -> list[StaticTransform]:
    """Returns the edge closest to `timestamp_ns` for each child frame.

    An edge captured more than `DYNAMIC_TRANSFORM_WINDOW_NS` from `timestamp_ns` is
    left out.
    """
    closest_by_child: dict[str, StaticTransform] = {}
    for transform in edges:
        offset_ns = abs(transform.timestamp_ns - timestamp_ns)
        if offset_ns > DYNAMIC_TRANSFORM_WINDOW_NS:
            continue
        closest = closest_by_child.get(transform.child_frame_id)
        if closest is None or offset_ns < abs(closest.timestamp_ns - timestamp_ns):
            closest_by_child[transform.child_frame_id] = transform
    return list(closest_by_child.values())


def transforms_of_message(
    decoder: ChannelDecoder,
    path: str,
    schema: Schema | None,
    channel: Channel,
    message: Message,
) -> list[StaticTransform]:
    """Returns the transforms of a message, or none if it cannot be read."""
    decoded_message = decoder.decoded_payload(schema=schema, channel=channel, message=message)
    if decoded_message is None:
        return []
    try:
        return transforms.from_decoded_message(decoded_message, log_time_ns=message.log_time)
    except McapAccessError:
        logger.warning(
            "Cannot read the transforms of a message of topic '%s' in '%s'. It is skipped.",
            channel.topic,
            path,
        )
        return []


def _read_dynamic_edges(
    mcap_reader: McapReader, path: str, topic: str, start_ns: int, end_ns: int
) -> list[StaticTransform]:
    """Returns the dynamic edges whose log time is in `[start_ns, end_ns)`.

    Raises:
        McapAccessError: If a message on the topic cannot be decoded.
    """
    edges: list[StaticTransform] = []
    try:
        for _, _, message, decoded_message in mcap_reader.iter_decoded_messages(
            topics=[topic], start_time=start_ns, end_time=end_ns
        ):
            edges.extend(
                transforms.from_decoded_message(decoded_message, log_time_ns=message.log_time)
            )
    except (DecoderNotFoundError, UnicodeDecodeError, ValueError) as exc:
        raise McapAccessError(
            f"Cannot decode the messages of topic '{topic}' in '{path}': {exc}"
        ) from exc
    return edges
