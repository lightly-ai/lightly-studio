"""Utilities for collecting and formatting request timing metrics."""

from __future__ import annotations

import time
from contextvars import ContextVar, Token
from dataclasses import dataclass


@dataclass
class RequestTimingState:
    """Mutable per-request timing state."""

    db_time_ms: float = 0.0


_request_timing_state: ContextVar[RequestTimingState | None] = ContextVar(
    "_request_timing_state",
    default=None,
)


def start_request_timing() -> tuple[float, Token[RequestTimingState | None]]:
    """Initialize timing state for the current request."""
    request_start_time = time.perf_counter()
    token = _request_timing_state.set(RequestTimingState())
    return request_start_time, token


def finish_request_timing(
    request_start_time: float,
    token: Token[RequestTimingState | None],
) -> tuple[float, float, float]:
    """Finalize timing state and return (total_ms, db_ms, backend_ms)."""
    total_ms = (time.perf_counter() - request_start_time) * 1000
    state = _request_timing_state.get()
    _request_timing_state.reset(token)

    db_ms = 0.0 if state is None else state.db_time_ms
    backend_ms = max(total_ms - db_ms, 0.0)
    return total_ms, db_ms, backend_ms


def add_db_time_ms(duration_ms: float) -> None:
    """Add database execution time to the active request."""
    state = _request_timing_state.get()
    if state is None:
        return
    state.db_time_ms += duration_ms


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
