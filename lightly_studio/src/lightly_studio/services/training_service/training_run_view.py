"""Build the API view of a training run."""

from __future__ import annotations

from pathlib import Path

from lightly_studio.models.training_run import TrainingRunStatus, TrainingRunView
from lightly_studio.services.training_service import parse_training_progress
from lightly_studio.services.training_service.training_run_registry import TrainingRun


def to_view(run: TrainingRun) -> TrainingRunView:
    """Return the view of a run, with the progress read from the files of the run."""
    progress = parse_training_progress.parse_training_progress(
        log_text=_read_text_or_empty(path=run.files.train_log_file)
    )
    return TrainingRunView(
        training_run_id=run.training_run_id,
        collection_id=run.collection_id,
        name=run.name,
        status=_status(run=run),
        model_name=run.model_name,
        steps=run.steps,
        train_sample_count=run.train_sample_count,
        val_sample_count=len(run.val_sample_ids),
        created_at=run.created_at,
        current_step=progress.current_step,
        total_steps=progress.total_steps,
        train_loss=progress.train_loss,
        evaluation_run_id=run.evaluation_run_id,
        error=run.error,
    )


def _status(run: TrainingRun) -> TrainingRunStatus:
    # Only the training process knows when it starts to predict. It writes the stage file.
    stage = _read_text_or_empty(path=run.files.stage_file).strip()
    if run.status == TrainingRunStatus.TRAINING and stage == "predicting":
        return TrainingRunStatus.PREDICTING
    return run.status


def _read_text_or_empty(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8", errors="replace")
