"""Capture timestamps from decoded MCAP messages.

ROS messages carry the time in `header.stamp`. Foxglove messages carry it in
`timestamp`. Both are `sec` plus `nanosec` (or `nsec`) since the Unix epoch.
Protobuf messages use `seconds` plus `nanos`.
"""

from __future__ import annotations

from typing import Any

from lightly_studio.core.mcap import message_fields
from lightly_studio.core.mcap.errors import McapAccessError

NANOSECONDS_PER_SECOND = 1_000_000_000

_HEADER_FIELDS = ("header",)
_STAMP_FIELDS = ("stamp", "timestamp")
_TIMESTAMP_FIELDS = ("timestamp",)
_SEC_FIELDS = ("sec", "seconds")
_NSEC_FIELDS = ("nsec", "nanosec", "nanoseconds", "nanos")


def from_decoded_message(decoded_message: Any) -> int:
    """Returns the capture time of a decoded message, in nanoseconds.

    Args:
        decoded_message: A decoded ROS or Foxglove message.

    Returns:
        The capture timestamp as nanoseconds since the Unix epoch.

    Raises:
        McapAccessError: If the message has no `header.stamp` or `timestamp`, or if
            the timestamp is not a number.
    """
    header = message_fields.get_field(decoded_message, _HEADER_FIELDS)
    stamp = None if header is None else message_fields.get_field(header, _STAMP_FIELDS)
    if stamp is None:
        stamp = message_fields.get_field(decoded_message, _TIMESTAMP_FIELDS)
    if stamp is None:
        raise McapAccessError("Message has no header stamp or timestamp.")
    return _timestamp_ns(stamp=stamp)


def _timestamp_ns(stamp: Any) -> int:
    """Returns a Time message as nanoseconds since the Unix epoch."""
    sec = message_fields.require_field(stamp, _SEC_FIELDS)
    nsec = message_fields.get_field(stamp, _NSEC_FIELDS)
    try:
        return int(sec) * NANOSECONDS_PER_SECOND + (0 if nsec is None else int(nsec))
    except (TypeError, ValueError) as error:
        raise McapAccessError(f"Timestamp is not a number: {stamp!r}.") from error
