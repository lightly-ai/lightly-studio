"""Decoders for the MCAP message encodings the access layer can read.

Only calibration and keyframe detection need decoded messages. Frame locators are
built from the message index alone.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from typing import Any

from mcap.decoder import DecoderFactory
from mcap.records import Schema
from mcap.well_known import MessageEncoding
from mcap_ros2 import decoder as ros2_decoder


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


def decoder_factories() -> list[DecoderFactory]:
    """Returns a decoder for every message encoding the access layer can read.

    Returns:
        Decoder factories for CDR-encoded ROS 2 messages and JSON messages.
    """
    return [
        ros2_decoder.DecoderFactory(),
        JsonDecoderFactory(),
    ]


def _decode_json(data: bytes) -> Any:
    """Decodes a JSON message payload."""
    return json.loads(data.decode("utf-8"))
