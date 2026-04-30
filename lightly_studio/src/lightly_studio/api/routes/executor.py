"""Shared thread pool executor registry for CPU-intensive media routes."""

from __future__ import annotations

import os
from concurrent.futures import ThreadPoolExecutor

_executors: dict[str, ThreadPoolExecutor] = {}


def get_media_executor(thread_name_prefix: str) -> ThreadPoolExecutor:
    """Return the executor for the given prefix, creating it on first call."""
    if thread_name_prefix not in _executors:
        cpu_count = os.cpu_count() or 1
        max_workers = max(1, min(cpu_count - 1 or 1, 16))
        _executors[thread_name_prefix] = ThreadPoolExecutor(
            max_workers=max_workers, thread_name_prefix=thread_name_prefix
        )
    return _executors[thread_name_prefix]
