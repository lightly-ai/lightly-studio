"""Unit tests for the bind-parameter batching helper."""

from __future__ import annotations

import pytest

from lightly_studio.utils import batching


def test_batched__chunks_with_remainder() -> None:
    assert list(batching.batched([1, 2, 3, 4, 5], batch_size=2)) == [[1, 2], [3, 4], [5]]


def test_batched__empty() -> None:
    assert list(batching.batched([], batch_size=3)) == []


def test_batched__rejects_non_positive_batch_size() -> None:
    with pytest.raises(ValueError, match="batch_size must be >= 1"):
        # The guard fires on first iteration, so the generator must be consumed.
        list(batching.batched([1], batch_size=0))
