"""Lazy, bounded parallel map over a thread pool.

``thread_imap_lazy`` applies a function across a thread pool while consuming its input
lazily: at most ``buffer_size`` items are read ahead of the caller and in flight at once.
Read-ahead is bounded to the consumer, so it scales to very large or unbounded inputs and
bounds any per-item resources (memory, temporary files) held by outstanding work.

Threads (not processes) suit I/O-bound or GIL-releasing work (network downloads, disk
reads, PyAV decode, torch/numpy): they overlap without the process spawn cost and input
pickling of multiprocessing, which under the "spawn" start method (e.g. macOS) makes
per-batch worker pools slower than a single thread.
"""

from __future__ import annotations

import itertools
from collections import deque
from collections.abc import Callable, Iterable, Iterator
from concurrent.futures import FIRST_COMPLETED, Future, ThreadPoolExecutor, wait
from typing import TypeVar

_T = TypeVar("_T")
_R = TypeVar("_R")


def thread_imap_lazy(
    function: Callable[[_T], _R],
    iterable: Iterable[_T],
    max_workers: int,
    buffer_size: int | None = None,
) -> Iterator[_R]:
    """Apply ``function`` across a thread pool, lazily and in input order.

    A threaded analogue of ``map`` for I/O-bound or GIL-releasing work. Unlike
    ``ThreadPoolExecutor.map``, the input is consumed lazily: at most ``buffer_size``
    items are read ahead of the caller and in flight at once. A new item is read and
    submitted only when the caller takes a result, so read-ahead stays bounded to the
    consumer even when ``function`` is fast. This scales to very large or unbounded
    inputs and bounds the per-item resources (memory, temporary files) held by
    outstanding work.

    Args:
        function: Work applied to each item. Called concurrently from worker threads, so
            it must be thread-safe with respect to any shared state it touches.
        iterable: Items to process. Consumed lazily, one look-ahead window at a time.
        max_workers: Number of worker threads. Must be at least 1.
        buffer_size: Maximum items in flight (submitted but not yet yielded). Defaults to
            ``max_workers``. Must be at least 1.

    Yields:
        ``function(item)`` for each item, in the order of ``iterable``.

    Raises:
        ValueError: If ``max_workers`` or ``buffer_size`` is less than 1.
    """
    buffer_size = _resolve_buffer_size(max_workers=max_workers, buffer_size=buffer_size)
    items = iter(iterable)
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # A FIFO queue of in-flight futures preserves input order on the way out.
        pending: deque[Future[_R]] = deque(
            executor.submit(function, item) for item in itertools.islice(items, buffer_size)
        )
        while pending:
            # Re-raises the worker's exception here, in the caller, if it failed.
            result = pending.popleft().result()
            # Refill only now that the caller is taking a result, so read-ahead stays
            # bounded to the consumer even when ``function`` is fast.
            try:
                next_item = next(items)
            except StopIteration:
                pass
            else:
                pending.append(executor.submit(function, next_item))
            yield result


def thread_imap_unordered_lazy(
    function: Callable[[_T], _R],
    iterable: Iterable[_T],
    max_workers: int,
    buffer_size: int | None = None,
) -> Iterator[_R]:
    """Apply ``function`` across a thread pool, lazily, yielding results as they complete.

    Like :func:`thread_imap_lazy` but order is not preserved: a slow item does not hold up
    faster ones behind it, which improves throughput when per-item durations vary (e.g.
    downloading files of very different sizes). Prefer this when the caller does not depend
    on input order. Read-ahead is bounded to the consumer exactly as in the ordered variant.

    Args:
        function: Work applied to each item. Called concurrently from worker threads, so
            it must be thread-safe with respect to any shared state it touches.
        iterable: Items to process. Consumed lazily, one look-ahead window at a time.
        max_workers: Number of worker threads. Must be at least 1.
        buffer_size: Maximum items in flight (submitted but not yet yielded). Defaults to
            ``max_workers``. Must be at least 1.

    Yields:
        ``function(item)`` for each item, in completion order.

    Raises:
        ValueError: If ``max_workers`` or ``buffer_size`` is less than 1.
    """
    buffer_size = _resolve_buffer_size(max_workers=max_workers, buffer_size=buffer_size)
    items = iter(iterable)
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        pending: set[Future[_R]] = {
            executor.submit(function, item) for item in itertools.islice(items, buffer_size)
        }
        while pending:
            done, pending = wait(pending, return_when=FIRST_COMPLETED)
            for future in done:
                try:
                    next_item = next(items)
                except StopIteration:
                    pass
                else:
                    pending.add(executor.submit(function, next_item))
                yield future.result()


def _resolve_buffer_size(max_workers: int, buffer_size: int | None) -> int:
    """Validate the pool sizing and resolve a ``None`` buffer size to ``max_workers``."""
    if max_workers < 1:
        raise ValueError(f"max_workers must be at least 1, got {max_workers}.")
    resolved = max_workers if buffer_size is None else buffer_size
    if resolved < 1:
        raise ValueError(f"buffer_size must be at least 1, got {resolved}.")
    return resolved
