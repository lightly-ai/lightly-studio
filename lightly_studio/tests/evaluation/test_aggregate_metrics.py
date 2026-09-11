"""Tests for confusion-matrix-derived aggregate metrics."""

from __future__ import annotations

import pytest

from lightly_studio.evaluation import aggregate_metrics
from lightly_studio.models.evaluation_confusion_matrix import (
    NO_GROUND_TRUTH_ROW_LABEL,
    NO_PREDICTION_COL_LABEL,
    ConfusionMatrix,
)
from lightly_studio.models.evaluation_metrics import ClassMetrics, EvaluationMetrics
from lightly_studio.models.evaluation_run import EvaluationTaskType


def _by_label(metrics: EvaluationMetrics) -> dict[str, ClassMetrics]:
    return {entry.label: entry for entry in metrics.per_class}


def test_classification_metrics() -> None:
    matrix = ConfusionMatrix(
        row_labels=["cat", "dog", NO_GROUND_TRUTH_ROW_LABEL],
        col_labels=["cat", "dog", NO_PREDICTION_COL_LABEL],
        counts=[
            [3, 1, 0],  # 3 cats correct, 1 cat predicted as dog
            [0, 4, 0],  # 4 dogs correct
            [0, 0, 0],
        ],
    )

    result = aggregate_metrics.compute_from_confusion_matrix(
        matrix=matrix, task_type=EvaluationTaskType.CLASSIFICATION
    )

    per_class = _by_label(result)
    assert per_class["cat"].precision == pytest.approx(1.0)  # 3 / (3 + 0)
    assert per_class["cat"].recall == pytest.approx(0.75)  # 3 / (3 + 1)
    assert per_class["cat"].f1 == pytest.approx(2 * 1.0 * 0.75 / 1.75)
    assert per_class["cat"].support == 4
    assert per_class["dog"].precision == pytest.approx(0.8)  # 4 / (1 + 4)
    assert per_class["dog"].recall == pytest.approx(1.0)  # 4 / 4
    assert per_class["dog"].support == 4
    # Micro-averaged over the pooled counts.
    assert result.precision == pytest.approx(0.875)  # 7 / 8
    assert result.recall == pytest.approx(0.875)  # 7 / 8
    assert result.f1 == pytest.approx(0.875)
    assert result.accuracy == pytest.approx(0.875)  # 7 correct / 8 samples


def test_detection_metrics_with_fp_and_fn_buckets() -> None:
    matrix = ConfusionMatrix(
        row_labels=["cat", NO_GROUND_TRUTH_ROW_LABEL],
        col_labels=["cat", NO_PREDICTION_COL_LABEL],
        counts=[
            [5, 2],  # 5 true positives, 2 false negatives (gt with no prediction)
            [3, 0],  # 3 false positives (prediction with no gt)
        ],
    )

    result = aggregate_metrics.compute_from_confusion_matrix(
        matrix=matrix, task_type=EvaluationTaskType.OBJECT_DETECTION
    )

    per_class = _by_label(result)
    assert per_class["cat"].precision == pytest.approx(5 / 8)  # 5 / (5 + 3)
    assert per_class["cat"].recall == pytest.approx(5 / 7)  # 5 / (5 + 2)
    assert per_class["cat"].support == 7
    assert result.precision == pytest.approx(5 / 8)
    assert result.recall == pytest.approx(5 / 7)
    # Accuracy is not defined for detection (predictions and ground truths are matched).
    assert result.accuracy is None


def test_zero_division_is_guarded() -> None:
    # "dog" is only ever predicted (never a ground truth): recall has a zero denominator.
    matrix = ConfusionMatrix(
        row_labels=["cat", "dog", NO_GROUND_TRUTH_ROW_LABEL],
        col_labels=["cat", "dog", NO_PREDICTION_COL_LABEL],
        counts=[
            [2, 0, 0],
            [0, 0, 0],
            [0, 3, 0],  # 3 predictions of "dog" with no ground truth
        ],
    )

    result = aggregate_metrics.compute_from_confusion_matrix(
        matrix=matrix, task_type=EvaluationTaskType.OBJECT_DETECTION
    )

    per_class = _by_label(result)
    assert per_class["dog"].precision == pytest.approx(0.0)  # 0 / 3
    assert per_class["dog"].recall == pytest.approx(0.0)  # 0 / 0 guarded
    assert per_class["dog"].f1 == pytest.approx(0.0)
    assert per_class["dog"].support == 0


def test_empty_matrix() -> None:
    matrix = ConfusionMatrix(row_labels=[], col_labels=[], counts=[])

    result = aggregate_metrics.compute_from_confusion_matrix(
        matrix=matrix, task_type=EvaluationTaskType.CLASSIFICATION
    )

    assert result.per_class == []
    assert result.precision == pytest.approx(0.0)
    assert result.recall == pytest.approx(0.0)
    assert result.f1 == pytest.approx(0.0)
    assert result.accuracy == pytest.approx(0.0)
