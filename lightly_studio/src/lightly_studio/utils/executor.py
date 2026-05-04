"""Shared thread pool executor registry for CPU-intensive media routes."""

from __future__ import annotations

import os
from concurrent.futures import ThreadPoolExecutor

_executors: dict[str, ThreadPoolExecutor] = {}


def get_media_executor(thread_name_prefix: str) -> ThreadPoolExecutor:
    """Return a shared ``ThreadPoolExecutor`` for CPU-intensive media processing.

    Executors are created lazily and cached by prefix, so each logical worker group
    gets its own pool while repeated calls reuse the existing one. Use this to
    offload blocking work (image resizing, frame extraction) from the async event loop.

    Args:
        thread_name_prefix: Label for worker thread names, e.g. ``"image_thumbnail"``.

    Returns:
        The cached ``ThreadPoolExecutor`` for the given prefix.
    """
    if thread_name_prefix not in _executors:
        cpu_count = os.cpu_count() or 1
        max_workers = max(1, min(cpu_count - 1 or 1, 16))
        _executors[thread_name_prefix] = ThreadPoolExecutor(
            max_workers=max_workers, thread_name_prefix=thread_name_prefix
        )
    return _executors[thread_name_prefix]
