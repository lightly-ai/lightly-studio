"""Reads camera intrinsics and static transforms from an open MCAP file."""

from __future__ import annotations

import logging
from collections.abc import Iterable, Iterator
from typing import Any

from mcap.reader import McapReader
from mcap.records import Channel, Message, Schema

from lightly_studio.core.mcap import camera_info, transforms
from lightly_studio.core.mcap.errors import McapAccessError
from lightly_studio.core.mcap.reader.session import ChannelDecoder
from lightly_studio.core.mcap.type_definitions import CameraIntrinsics, StaticTransform

logger = logging.getLogger(__name__)

STATIC_TRANSFORM_TOPIC = "/tf_static"
DYNAMIC_TRANSFORM_TOPIC = "/tf"


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
) -> Iterator[StaticTransform]:
    """Reads the transforms of every message on a topic, skipping unreadable messages.

    Args:
        mcap_reader: The seeking reader of the open file.
        decoder: Decodes a payload, or skips a message that cannot be decoded.
        path: The path or URI of the MCAP file, used in skip warnings.
        topic: The topic to read. The topic is in the file.

    Returns:
        One transform per edge in the topic, read lazily. A message that cannot be
        decoded, or holds no transform, is skipped.
    """
    return (
        transform
        for schema, channel, message in mcap_reader.iter_messages(topics=[topic])
        for transform in transforms_of_message(
            decoder=decoder, path=path, schema=schema, channel=channel, message=message
        )
    )


def unique_edges(static_transforms: Iterable[StaticTransform]) -> list[tuple[str, str]]:
    """Returns the parent and child frame of each transform, once, in order of appearance."""
    return list(
        dict.fromkeys(
            (transform.parent_frame_id, transform.child_frame_id) for transform in static_transforms
        )
    )


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
