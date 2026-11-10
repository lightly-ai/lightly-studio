"""Cancel an active training run."""

from __future__ import annotations

from uuid import UUID

from lightly_studio.errors import NotFoundError
from lightly_studio.models.training_run import TrainingRunStatus
from lightly_studio.services.training_service.training_run_registry import (
    TrainingRun,
    TrainingRunRegistry,
)

_CANCELLABLE_STATUSES = frozenset((TrainingRunStatus.TRAINING, TrainingRunStatus.PREDICTING))


def cancel_training_run(
    registry: TrainingRunRegistry, collection_id: UUID, training_run_id: UUID
) -> TrainingRun:
    """Stop the training process of a run. The watcher thread then marks it as cancelled.

    Raises:
        NotFoundError: If the collection has no run with this ID.
        ValueError: If the training process of the run is not running.
    """
    run = registry.get(training_run_id=training_run_id)
    if run is None or run.collection_id != collection_id:
        raise NotFoundError(f"Training run {training_run_id} not found.")
    if run.status not in _CANCELLABLE_STATUSES or run.process is None:
        raise ValueError("Only a run that is training or predicting can be cancelled.")
    run.cancel_requested = True
    run.process.terminate()
    return run
