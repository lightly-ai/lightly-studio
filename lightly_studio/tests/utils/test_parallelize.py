import itertools
import threading
from collections.abc import Iterator

import pytest

from lightly_studio.utils import parallelize


def test_thread_imap_lazy() -> None:
    result = list(parallelize.thread_imap_lazy(lambda x: x * 2, range(10), max_workers=4))
    assert result == [x * 2 for x in range(10)]


def test_thread_imap_lazy__empty() -> None:
    empty: list[int] = []
    result = list(parallelize.thread_imap_lazy(lambda x: x, empty, max_workers=4))
    assert result == []


def test_thread_imap_lazy__preserves_order_despite_out_of_order_completion() -> None:
    # Item 0 finishes only after item 1 has run, forcing completion order 1 then 0.
    # The output must still be in input order.
    item_1_done = threading.Event()

    def func(x: int) -> int:
        if x == 0:
            item_1_done.wait(timeout=5)
        else:
            item_1_done.set()
        return x

    result = list(parallelize.thread_imap_lazy(func, [0, 1], max_workers=2, buffer_size=2))
    assert result == [0, 1]


def test_thread_imap_lazy__reads_ahead_bounded_by_buffer_size() -> None:
    # Read-ahead must stay bounded to the consumer even for a fast function and an
    # unbounded source: taking one result reads exactly one more item.
    pulled = 0

    def source() -> Iterator[int]:
        nonlocal pulled
        for i in itertools.count():
            pulled += 1
            yield i

    buffer_size = 3
    iterator = iter(
        parallelize.thread_imap_lazy(lambda x: x, source(), max_workers=2, buffer_size=buffer_size)
    )
    assert next(iterator) == 0
    # Initial fill reads buffer_size items; taking one result refills exactly one.
    assert pulled == buffer_size + 1


def test_thread_imap_lazy__reraises_function_error() -> None:
    def func(x: int) -> int:
        if x == 3:
            raise ValueError("boom")
        return x

    yielded = []

    def consume() -> None:
        for result in parallelize.thread_imap_lazy(func, range(10), max_workers=2, buffer_size=2):
            yielded.append(result)

    with pytest.raises(ValueError, match="boom"):
        consume()
    assert yielded == [0, 1, 2]


@pytest.mark.parametrize("max_workers", [0, -1])
def test_thread_imap_lazy__invalid_max_workers(max_workers: int) -> None:
    with pytest.raises(ValueError, match="max_workers must be at least 1"):
        list(parallelize.thread_imap_lazy(lambda x: x, [1, 2], max_workers=max_workers))


def test_thread_imap_lazy__invalid_buffer_size() -> None:
    with pytest.raises(ValueError, match="buffer_size must be at least 1"):
        list(parallelize.thread_imap_lazy(lambda x: x, [1, 2], max_workers=2, buffer_size=0))


def test_thread_imap_unordered_lazy__yields_all_results() -> None:
    results = parallelize.thread_imap_unordered_lazy(lambda x: x, range(20), max_workers=5)
    assert sorted(results) == list(range(20))


def test_thread_imap_unordered_lazy__reads_ahead_bounded_by_buffer_size() -> None:
    pulled = 0

    def source() -> Iterator[int]:
        nonlocal pulled
        for i in itertools.count():
            pulled += 1
            yield i

    buffer_size = 3
    iterator = iter(
        parallelize.thread_imap_unordered_lazy(
            lambda x: x, source(), max_workers=2, buffer_size=buffer_size
        )
    )
    next(iterator)
    assert pulled == buffer_size + 1


def test_thread_imap_unordered_lazy__invalid_max_workers() -> None:
    with pytest.raises(ValueError, match="max_workers must be at least 1"):
        list(parallelize.thread_imap_unordered_lazy(lambda x: x, [1, 2], max_workers=0))
