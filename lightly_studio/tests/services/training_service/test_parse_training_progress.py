from __future__ import annotations

from lightly_studio.services.training_service import parse_training_progress
from lightly_studio.services.training_service.parse_training_progress import TrainingProgress


def test_parse_training_progress() -> None:
    log_text = (
        "Resolved Args: ...\n"
        "Train Step  10/100 | Epoch 0 | train_loss: 2.5000 | lr: 0.00010000\n"
        "Train Step  20/100 | Epoch 0 | train_loss: 1.2500 | lr: 0.00010000\n"
        "Val Step 1/1 | val_loss: 1.1000\n"
    )

    progress = parse_training_progress.parse_training_progress(log_text=log_text)

    assert progress == TrainingProgress(current_step=20, total_steps=100, train_loss=1.25)


def test_parse_training_progress__no_loss() -> None:
    progress = parse_training_progress.parse_training_progress(
        log_text="Train Step 3/7 | Epoch 0\n"
    )

    assert progress == TrainingProgress(current_step=3, total_steps=7, train_loss=None)


def test_parse_training_progress__no_step_line() -> None:
    assert parse_training_progress.parse_training_progress(log_text="") == TrainingProgress()
    assert (
        parse_training_progress.parse_training_progress(log_text="Resolved Args: ...\nTrain Ste")
        == TrainingProgress()
    )
