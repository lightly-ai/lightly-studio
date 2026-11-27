"""Encodes the payloads of one tick as one HTTP response body."""

from __future__ import annotations

import struct
from collections.abc import Sequence

from lightly_studio.services.recording_service.get_tick_data import TickPayload

MEDIA_TYPE = "application/octet-stream"

# Each payload is prefixed with its channel id (u32), its kind (u8), its log time
# (u64) and its length in bytes (u64), little-endian and without padding.
_HEADER = struct.Struct("<IBQQ")


def encode_tick_payloads(payloads: Sequence[TickPayload]) -> bytes:
    """Concatenates the payloads, each prefixed with its header.

    Args:
        payloads: The payloads to encode, in order.

    Returns:
        The frames `[channel_id][kind][log_time_ns][length][data]` of all payloads.
    """
    return b"".join(
        _HEADER.pack(payload.channel_id, payload.kind, payload.log_time_ns, len(payload.data))
        + payload.data
        for payload in payloads
    )
