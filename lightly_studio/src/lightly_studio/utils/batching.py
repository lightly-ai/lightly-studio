"""Batch bulk database operations to stay under PostgreSQL's 65,535 bind-parameter limit."""

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


def batched(items: Iterable[_T], batch_size: int | None = None) -> Iterator[list[_T]]:
    """Yield successive lists of at most ``batch_size`` items.

    Args:
        items: Iterable to split into batches.
        batch_size: Maximum items per batch; defaults to ``DEFAULT_BATCH_SIZE``. Must be >= 1.

    Yields:
        Lists of up to ``batch_size`` items; nothing if ``items`` is empty.

    Raises:
        ValueError: If the resolved batch size is less than 1.
    """
    size = DEFAULT_BATCH_SIZE if batch_size is None else batch_size
    if size < 1:
        raise ValueError(f"batch_size must be >= 1, got {size}.")
    iterator = iter(items)
    while batch := list(itertools.islice(iterator, size)):
        yield batch
