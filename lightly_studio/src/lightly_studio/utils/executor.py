"""Shared thread pool executor registry for routes that offload blocking work."""

from __future__ import annotations

import os
from concurrent.futures import ThreadPoolExecutor

_executors: dict[str, ThreadPoolExecutor] = {}


def get_media_worker_count() -> int:
    """Return the worker count for parallel media processing."""
    cpu_count = os.cpu_count() or 1
    return max(1, min(cpu_count - 1 or 1, 16))


def get_media_executor(
    thread_name_prefix: str, max_workers: int | None = None
) -> ThreadPoolExecutor:
    """Return a shared ``ThreadPoolExecutor`` for blocking work.

    Executors are created lazily and cached by prefix, so each logical worker group
    gets its own pool while repeated calls reuse the existing one. Use this to
    offload blocking work (image resizing, frame extraction, network calls) from the
    async event loop.

    Args:
        thread_name_prefix: Label for worker thread names, e.g. ``"image_thumbnail"``.
        max_workers: Worker count of the pool. Defaults to ``get_media_worker_count()``,
            which suits CPU-bound work. Only the first call for a prefix sets it.

    Returns:
        The cached ``ThreadPoolExecutor`` for the given prefix.
    """
    if thread_name_prefix not in _executors:
        _executors[thread_name_prefix] = ThreadPoolExecutor(
            max_workers=max_workers or get_media_worker_count(),
            thread_name_prefix=thread_name_prefix,
        )
    return _executors[thread_name_prefix]
