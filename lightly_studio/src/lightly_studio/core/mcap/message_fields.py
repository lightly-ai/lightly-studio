"""Field access for decoded MCAP messages.

A decoded message is a ROS 2 object, a protobuf object, or a plain dict, depending
on how the file encodes its messages. The ROS and Foxglove flavours of the same
message also name their fields differently, e.g. `k` and `K` for the camera matrix.
These helpers read a field by any of its known names from any of the representations.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from types import SimpleNamespace
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
        if _is_mapping(message):
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
        if _is_mapping(message):
            if name in message:
                return message[name]
        elif hasattr(message, name):
            return getattr(message, name)
    expected = ", ".join(f"'{name}'" for name in names)
    raise McapAccessError(f"Message of type '{type(message).__name__}' has no field {expected}.")


def _is_mapping(message: Any) -> bool:
    """Returns whether a decoded message is read by key rather than by attribute.

    `mcap_ros2` creates a new `SimpleNamespace` subclass for every decoded message, so
    `isinstance` against the `Mapping` ABC never hits the ABC cache and checks every
    registered subclass. The concrete types are checked first, so that reading the
    fields of many ROS messages stays fast.
    """
    if isinstance(message, dict):
        return True
    if isinstance(message, SimpleNamespace):
        return False
    return isinstance(message, Mapping)
