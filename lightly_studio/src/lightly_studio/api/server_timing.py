"""Utilities for collecting and formatting request timing metrics."""

from __future__ import annotations

import time
from contextvars import ContextVar, Token

_request_db_time_ms: ContextVar[float | None] = ContextVar(
    "_request_db_time_ms",
    default=None,
)


def start_request_timing() -> tuple[float, Token[float | None]]:
    """Initialize timing state for the current request."""
    request_start_time = time.perf_counter()
    token = _request_db_time_ms.set(0.0)
    return request_start_time, token


def finish_request_timing(
    request_start_time: float,
    token: Token[float | None],
) -> tuple[float, float, float]:
    """Finalize timing state and return (total_ms, db_ms, backend_ms)."""
    total_ms = (time.perf_counter() - request_start_time) * 1000
    db_ms = _request_db_time_ms.get()
    _request_db_time_ms.reset(token)

    db_ms = 0.0 if db_ms is None else db_ms
    backend_ms = max(total_ms - db_ms, 0.0)
    return total_ms, db_ms, backend_ms


def add_db_time_ms(duration_ms: float) -> None:
    """Add database execution time to the active request."""
    current_db_time_ms = _request_db_time_ms.get()
    if current_db_time_ms is None:
        return
    _request_db_time_ms.set(current_db_time_ms + duration_ms)


def format_server_timing_header(
    total_ms: float,
    db_ms: float,
    backend_ms: float,
) -> str:
    """Format the Server-Timing response header value."""
    return (
        f"total;dur={total_ms:.1f},"
        f" db;dur={db_ms:.1f},"
        f" backend;dur={backend_ms:.1f}"
    )
