"""Split an iterable into batches of a bounded size."""

from __future__ import annotations

import itertools
from collections.abc import Iterable, Iterator
from typing import TypeVar

_T = TypeVar("_T")

# One batch size for both IN-clauses (one parameter per element) and multi-row INSERTs
# (rows x columns). 8000 keeps any single statement well under PostgreSQL's 65,535
# bind-parameter cap (inserts up to 8 columns; the only single-statement inserts here
# have at most 4). Wider tables use bulk_save_objects, which SQLAlchemy auto-paginates.
DEFAULT_BATCH_SIZE = 8_000


def batched(items: Iterable[_T], batch_size: int = DEFAULT_BATCH_SIZE) -> Iterator[list[_T]]:
    """Yield successive lists of at most ``batch_size`` items; raises ValueError if < 1."""
    if batch_size < 1:
        raise ValueError(f"batch_size must be >= 1, got {batch_size}.")
    iterator = iter(items)
    while batch := list(itertools.islice(iterator, batch_size)):
        yield batch


def batch_count(total_items: int, batch_size: int = DEFAULT_BATCH_SIZE) -> int:
    """Number of batches ``batched`` yields for ``total_items`` items.

    Args:
        total_items: Number of items to be batched. Must not be negative.
        batch_size: Maximum items per batch. Must be at least 1.

    Returns:
        The number of batches, rounding a partial final batch up.

    Raises:
        ValueError: If ``batch_size`` is less than 1 or ``total_items`` is negative.
    """
    if batch_size < 1:
        raise ValueError(f"batch_size must be >= 1, got {batch_size}.")
    if total_items < 0:
        raise ValueError(f"total_items must be >= 0, got {total_items}.")
    return (total_items + batch_size - 1) // batch_size
