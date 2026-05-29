"""Helpers to keep bulk database operations under the parameter limit.

PostgreSQL caps a single statement at 65,535 bind parameters (the wire protocol
encodes the parameter count as an ``Int16``). Bulk operations whose parameter
count scales with the dataset size therefore have to be split into batches:

- An ``IN (...)`` clause binds one parameter per element, so id lists are
  chunked into :data:`IN_CLAUSE_BATCH_SIZE` pieces.
- A multi-row ``INSERT ... VALUES`` binds ``rows * columns`` parameters, so the
  row count is chunked into :data:`INSERT_BATCH_SIZE` pieces.

Chunking is dialect-agnostic: it is required for PostgreSQL and harmless for
DuckDB, so the same code path is used for both backends.
"""

from __future__ import annotations

import itertools
from collections.abc import Iterable, Iterator
from typing import TypeVar

_T = TypeVar("_T")

# PostgreSQL hard cap on bind parameters per single statement.
MAX_POSTGRES_BIND_PARAMS = 65_535
# Batch size for ``IN (...)`` lists (one parameter per element). The large
# headroom leaves room for one or two extra scalar predicates in the statement.
IN_CLAUSE_BATCH_SIZE = 30_000
# Batch size (rows) for a single multi-row ``INSERT ... VALUES`` statement, which
# binds ``rows * columns`` parameters. 4,000 stays under the cap for any insert of
# up to 16 columns (4,000 * 16 < 65,535); wider tables are inserted via
# ``session.bulk_save_objects``, which SQLAlchemy auto-pages per statement.
INSERT_BATCH_SIZE = 4_000


def batched(items: Iterable[_T], batch_size: int) -> Iterator[list[_T]]:
    """Yield successive lists of at most ``batch_size`` items from ``items``.

    Args:
        items: Any iterable to split into batches.
        batch_size: Maximum number of items per batch. Must be >= 1.

    Yields:
        Lists of length ``batch_size`` except possibly the last, which holds the
        remainder. Yields nothing if ``items`` is empty.

    Raises:
        ValueError: If ``batch_size`` is less than 1 (raised on first iteration).
    """
    if batch_size < 1:
        raise ValueError(f"batch_size must be >= 1, got {batch_size}.")
    iterator = iter(items)
    while batch := list(itertools.islice(iterator, batch_size)):
        yield batch
