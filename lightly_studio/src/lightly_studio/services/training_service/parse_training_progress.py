"""Read the training progress from the LightlyTrain log."""

from __future__ import annotations

import re
from dataclasses import dataclass

# LightlyTrain pads the step to the width of the total, e.g. "Train Step  10/100".
_STEP_PATTERN = re.compile(r"Train Step\s+(\d+)/\s*(\d+)")
_LOSS_PATTERN = re.compile(r"train_loss: ([-+0-9.eE]+)")


@dataclass(frozen=True)
class TrainingProgress:
    """The progress of a training run. A value is None before LightlyTrain logs it."""

    current_step: int | None = None
    total_steps: int | None = None
    train_loss: float | None = None


def parse_training_progress(log_text: str) -> TrainingProgress:
    """Return the progress from the last train step line of a LightlyTrain log.

    Args:
        log_text: The content of `train.log`. It can be empty or end in a partial line.

    Returns:
        The step, total steps and train loss of the last train step line.
    """
    for line in reversed(log_text.splitlines()):
        step_match = _STEP_PATTERN.search(line)
        if step_match is None:
            continue
        loss_match = _LOSS_PATTERN.search(line)
        return TrainingProgress(
            current_step=int(step_match.group(1)),
            total_steps=int(step_match.group(2)),
            train_loss=float(loss_match.group(1)) if loss_match else None,
        )
    return TrainingProgress()
