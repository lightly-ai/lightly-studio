"""In-memory store of the training runs of the running Studio app."""

from __future__ import annotations

import subprocess
import threading
from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID

from lightly_studio.models.training_run import ACTIVE_TRAINING_RUN_STATUSES, TrainingRunStatus
from lightly_studio.services.training_service.training_run_files import TrainingRunFiles


@dataclass
class TrainingRun:
    """The state of one training run.

    The request thread creates the run. After that, only the watcher thread of the run
    changes it, except for `cancel_requested`.
    """

    training_run_id: UUID
    collection_id: UUID
    name: str
    model_name: str
    steps: int
    files: TrainingRunFiles
    gt_annotation_source: str
    val_sample_ids: list[UUID]
    train_sample_count: int
    created_at: datetime
    status: TrainingRunStatus = TrainingRunStatus.TRAINING
    process: subprocess.Popen[bytes] | None = None
    cancel_requested: bool = False
    evaluation_run_id: UUID | None = None
    error: str | None = None


@dataclass
class TrainingRunRegistry:
    """Keeps the training runs in memory. The runs are lost when Studio stops."""

    _runs: dict[UUID, TrainingRun] = field(default_factory=dict)
    _lock: threading.Lock = field(default_factory=threading.Lock)

    def add(self, run: TrainingRun) -> None:
        """Add a run. Raises a ValueError if a different run is active."""
        with self._lock:
            if any(r.status in ACTIVE_TRAINING_RUN_STATUSES for r in self._runs.values()):
                raise ValueError("A training run is already active. Wait for it or cancel it.")
            self._runs[run.training_run_id] = run

    def get(self, training_run_id: UUID) -> TrainingRun | None:
        """Return the run with the given ID, or None."""
        with self._lock:
            return self._runs.get(training_run_id)

    def list_for_collection(self, collection_id: UUID) -> list[TrainingRun]:
        """Return the runs of a collection, newest first."""
        with self._lock:
            runs = [r for r in self._runs.values() if r.collection_id == collection_id]
        return sorted(runs, key=lambda r: r.created_at, reverse=True)

    def has_active_run(self) -> bool:
        """Return whether a run is active."""
        with self._lock:
            return any(r.status in ACTIVE_TRAINING_RUN_STATUSES for r in self._runs.values())


training_run_registry = TrainingRunRegistry()
