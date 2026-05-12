"""Sort direction enum."""

from __future__ import annotations

from enum import Enum


class SortDirection(str, Enum):
    """Sort direction for a sort field expression."""

    asc = "asc"
    desc = "desc"
