"""Field access for decoded MCAP messages.

A decoded message is a ROS 2 object, a protobuf object, or a plain dict, depending
on how the file encodes its messages. The ROS and Foxglove flavours of the same
message also name their fields differently, e.g. `k` and `K` for the camera matrix.
These helpers read a field by any of its known names from any of the representations.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from lightly_studio.core.mcap.errors import McapAccessError


def get_field(message: Any, names: Sequence[str]) -> Any:
    """Returns the value of the first field the message has.

    Args:
        message: A decoded MCAP message or one of its nested values.
        names: The field names to look for, in order of preference.

    Returns:
        The value of the first field that the message has, or `None` if it has none
        of them.
    """
    for name in names:
        if isinstance(message, Mapping):
            if name in message:
                return message[name]
        elif hasattr(message, name):
            return getattr(message, name)
    return None


def require_field(message: Any, names: Sequence[str]) -> Any:
    """Returns the value of the first field the message has.

    Args:
        message: A decoded MCAP message or one of its nested values.
        names: The field names to look for, in order of preference.

    Returns:
        The value of the first field that the message has.

    Raises:
        McapAccessError: If the message has none of the fields.
    """
    for name in names:
        if isinstance(message, Mapping):
            if name in message:
                return message[name]
        elif hasattr(message, name):
            return getattr(message, name)
    expected = ", ".join(f"'{name}'" for name in names)
    raise McapAccessError(f"Message of type '{type(message).__name__}' has no field {expected}.")
