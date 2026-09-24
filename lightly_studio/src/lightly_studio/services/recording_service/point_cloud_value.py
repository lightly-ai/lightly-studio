"""Access fields from decoded ROS messages and mappings."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any


def get_value(value: object, name: str) -> Any:
    """Read a field from a decoded ROS message or mapping."""
    if isinstance(value, Mapping):
        return value[name]
    return getattr(value, name)
