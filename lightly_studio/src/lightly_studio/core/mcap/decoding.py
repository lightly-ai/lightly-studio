"""Decoders for the MCAP message encodings the access layer can read.

Calibration, keyframe detection, and annotation MCAP SceneUpdate need decoded
messages. Frame locators are built from the message index alone.
"""

from __future__ import annotations

import json
import re
from collections.abc import Callable
from typing import Any

from mcap.decoder import DecoderFactory
from mcap.records import Schema
from mcap.well_known import MessageEncoding, SchemaEncoding
from mcap_ros2 import decoder as ros2_decoder

# Foxglove ROS 1 SceneEntity uses these primitives. The ROS 2 decoder lists them
# as types but does not parse them. Map them to the builtin nested types instead.
_ROS1_TIME_TYPE = re.compile(r"^([ \t]*)time(?=[\s\[])", re.MULTILINE)
_ROS1_DURATION_TYPE = re.compile(r"^([ \t]*)duration(?=[\s\[])", re.MULTILINE)


class JsonDecoderFactory(DecoderFactory):
    """Decodes JSON-encoded messages into plain dicts."""

    def decoder_for(
        self,
        message_encoding: str,
        schema: Schema | None,  # noqa: ARG002
    ) -> Callable[[bytes], Any] | None:
        """Returns a decoder for JSON-encoded messages.

        Args:
            message_encoding: The message encoding of the channel.
            schema: The schema of the channel, unused because JSON is self describing.

        Returns:
            A decoder, or `None` if the messages are not JSON-encoded.
        """
        if message_encoding != MessageEncoding.JSON:
            return None
        return _decode_json


class Ros2DecoderFactory(DecoderFactory):
    """Decodes CDR-encoded ROS 2 messages.

    Foxglove SceneEntity definitions use the ROS 1 `time` and `duration` field
    types. The ROS 2 decoder treats those as unimplemented primitives. This
    factory maps them to `builtin_interfaces/Time` and
    `builtin_interfaces/Duration` before decode.
    """

    def __init__(self) -> None:
        """Wraps the ROS 2 CDR decoder so ROS 1 time fields can be rewritten."""
        self._inner = ros2_decoder.DecoderFactory()

    def decoder_for(
        self,
        message_encoding: str,
        schema: Schema | None,
    ) -> Callable[[bytes], Any] | None:
        """Returns a decoder for CDR-encoded ROS 2 messages.

        Args:
            message_encoding: The message encoding of the channel.
            schema: The schema of the channel, or `None` if the channel has none.

        Returns:
            A decoder, or `None` if the messages are not CDR-encoded ROS 2.
        """
        return self._inner.decoder_for(
            message_encoding=message_encoding,
            schema=_schema_with_ros2_time_types(schema=schema),
        )


def decoder_factories() -> list[DecoderFactory]:
    """Returns a decoder for every message encoding the access layer can read.

    Returns:
        Decoder factories for CDR-encoded ROS 2 messages and JSON messages.
    """
    return [
        Ros2DecoderFactory(),
        JsonDecoderFactory(),
    ]


def _decode_json(data: bytes) -> Any:
    """Decodes a JSON message payload."""
    return json.loads(data.decode("utf-8"))


def _schema_with_ros2_time_types(schema: Schema | None) -> Schema | None:
    """Returns a schema whose ROS 1 `time`/`duration` fields use builtin types."""
    if schema is None or schema.encoding != SchemaEncoding.ROS2:
        return schema
    try:
        schema_text = schema.data.decode()
    except UnicodeDecodeError:
        return schema
    rewritten = _rewrite_ros1_time_types(schema_text=schema_text)
    if rewritten == schema_text:
        return schema
    return Schema(id=schema.id, name=schema.name, encoding=schema.encoding, data=rewritten.encode())


def _rewrite_ros1_time_types(schema_text: str) -> str:
    """Replaces ROS 1 `time`/`duration` field types with builtin ROS 2 types."""
    rewritten = _ROS1_TIME_TYPE.sub(r"\1builtin_interfaces/Time", schema_text)
    return _ROS1_DURATION_TYPE.sub(r"\1builtin_interfaces/Duration", rewritten)
