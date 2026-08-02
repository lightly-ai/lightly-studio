"""Progress reporting for long-running operator executions.

Operators receive a ``report_progress`` callable through their
``ExecutionContext``. Calls land in the module-level ``progress_store``, which
the ``GET /operators/runs/{run_id}/progress`` route reads while the blocking
``execute`` request is still in flight.
"""

from __future__ import annotations

import threading
from dataclasses import dataclass
from uuid import UUID


@dataclass
class OperatorProgress:
    """Progress of a single operator run."""

    current: int
    """Number of units processed so far."""

    total: int
    """Total number of units to process. Zero when the total is not yet known."""

    description: str = ""
    """Human-readable description of the current step."""


class ProgressStore:
    """Thread-safe store holding the latest progress of in-flight operator runs.

    FastAPI dispatches synchronous route handlers to its worker threadpool, so
    concurrent operator runs report progress from different threads while the
    polling route reads from yet another one. The lock guards the dict against
    those concurrent accesses.

    Entries are transient: the execute route removes a run's entry once the
    operator returns, so the store only ever holds in-flight runs.
    """

    def __init__(self) -> None:
        """Initialize an empty progress store."""
        self._lock = threading.Lock()
        self._progress: dict[UUID, OperatorProgress] = {}

    def set(self, run_id: UUID, progress: OperatorProgress) -> None:
        """Record the latest progress of a run, replacing any previous value."""
        with self._lock:
            self._progress[run_id] = progress

    def get(self, run_id: UUID) -> OperatorProgress | None:
        """Return the latest progress of a run, or None if the run is unknown."""
        with self._lock:
            return self._progress.get(run_id)

    def clear(self, run_id: UUID) -> None:
        """Remove a run's progress. Does nothing if the run is unknown."""
        with self._lock:
            self._progress.pop(run_id, None)

    def get_run_ids(self) -> list[UUID]:
        """Return the ids of all runs currently holding progress."""
        with self._lock:
            return list(self._progress)


# Global progress store instance.
progress_store = ProgressStore()
