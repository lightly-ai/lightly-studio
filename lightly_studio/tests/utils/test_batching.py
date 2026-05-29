"""Unit tests for the bind-parameter batching helpers."""

from __future__ import annotations

import pytest

from lightly_studio.utils import batching


def test_batched__empty() -> None:
    assert list(batching.batched([], 3)) == []


def test_batched__exact_multiple() -> None:
    assert list(batching.batched([1, 2, 3, 4], 2)) == [[1, 2], [3, 4]]


def test_batched__remainder() -> None:
    assert list(batching.batched([1, 2, 3, 4, 5], 2)) == [[1, 2], [3, 4], [5]]


def test_batched__batch_larger_than_input() -> None:
    assert list(batching.batched([1, 2], 10)) == [[1, 2]]


def test_batched__batch_size_one() -> None:
    assert list(batching.batched([1, 2, 3], 1)) == [[1], [2], [3]]


def test_batched__consumes_generator() -> None:
    # A single-pass iterable must be supported, not just sequences.
    assert list(batching.batched((i for i in range(5)), 3)) == [[0, 1, 2], [3, 4]]


def test_batched__batch_size_zero_raises() -> None:
    with pytest.raises(ValueError, match="batch_size must be >= 1"):
        # The guard fires on first iteration, so the generator must be consumed.
        list(batching.batched([1], 0))


def test_batched__negative_batch_size_raises() -> None:
    with pytest.raises(ValueError, match="batch_size must be >= 1"):
        list(batching.batched([1], -1))


def test_insert_batch_size__stays_under_postgres_limit_up_to_16_columns() -> None:
    # A full INSERT batch must not exceed the hard cap for any insert up to 16
    # columns (single-statement inserts in the codebase have far fewer).
    for num_columns in range(1, 17):
        params = batching.INSERT_BATCH_SIZE * num_columns
        assert params <= batching.MAX_POSTGRES_BIND_PARAMS
