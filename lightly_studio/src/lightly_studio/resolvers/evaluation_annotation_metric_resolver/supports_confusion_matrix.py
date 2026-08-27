"""Decide which evaluation task types have a confusion matrix."""

from __future__ import annotations

from lightly_studio.models.evaluation_run import EvaluationTaskType

# Task types whose per-annotation pairings (ground-truth label x prediction
# label) aggregate into a confusion matrix. Segmentation tasks are not included.
_TASK_TYPES_WITH_CONFUSION_MATRIX = (
    EvaluationTaskType.OBJECT_DETECTION,
    EvaluationTaskType.CLASSIFICATION,
)


def supports_confusion_matrix(task_type: EvaluationTaskType) -> bool:
    """Return True if the task type aggregates into a confusion matrix."""
    return task_type in _TASK_TYPES_WITH_CONFUSION_MATRIX
