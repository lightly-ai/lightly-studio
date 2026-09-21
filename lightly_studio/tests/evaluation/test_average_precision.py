"""Tests for detection mean-average-precision computation."""

from __future__ import annotations

from uuid import UUID, uuid4

import pytest

from lightly_studio.evaluation import average_precision
from lightly_studio.evaluation.object_detection_metric import BoundingBox
from lightly_studio.models.evaluation_metrics import DetectionAveragePrecision

CAT = uuid4()
DOG = uuid4()
LABEL_NAMES = {CAT: "cat", DOG: "dog"}


def _box(  # noqa: PLR0913
    label_id: UUID,
    x: int,
    y: int,
    width: int = 10,
    height: int = 10,
    confidence: float | None = None,
) -> BoundingBox:
    return BoundingBox(
        annotation_id=uuid4(),
        x=x,
        y=y,
        width=width,
        height=height,
        label_id=label_id,
        confidence=confidence,
    )


def _ap_by_label(result: DetectionAveragePrecision) -> dict[str, float]:
    return {entry.label: entry.average_precision for entry in result.per_class}


def test_perfect_detection_has_ap_one() -> None:
    gt = [[_box(CAT, 0, 0)]]
    pred = [[_box(CAT, 0, 0, confidence=0.9)]]

    result = average_precision.compute(
        gt_per_image=gt, pred_per_image=pred, label_names=LABEL_NAMES, iou_thresholds=[0.5]
    )

    assert _ap_by_label(result) == {"cat": pytest.approx(1.0)}
    assert result.mean_average_precision == pytest.approx(1.0)


def test_high_confidence_false_positive_halves_ap() -> None:
    # One ground truth. A high-confidence prediction misses, a lower one hits.
    gt = [[_box(CAT, 0, 0)]]
    pred = [[_box(CAT, 500, 500, confidence=0.9), _box(CAT, 0, 0, confidence=0.8)]]

    result = average_precision.compute(
        gt_per_image=gt, pred_per_image=pred, label_names=LABEL_NAMES, iou_thresholds=[0.5]
    )

    # Precision is 0.5 across the recall range, so 101-point AP is 0.5.
    assert _ap_by_label(result) == {"cat": pytest.approx(0.5)}


def test_mean_over_classes() -> None:
    gt = [[_box(CAT, 0, 0), _box(DOG, 0, 0)]]
    pred = [
        [
            _box(CAT, 0, 0, confidence=0.9),  # cat true positive -> AP 1.0
            _box(DOG, 500, 500, confidence=0.9),  # dog false positive
            _box(DOG, 0, 0, confidence=0.8),  # dog true positive -> AP 0.5
        ]
    ]

    result = average_precision.compute(
        gt_per_image=gt, pred_per_image=pred, label_names=LABEL_NAMES, iou_thresholds=[0.5]
    )

    assert _ap_by_label(result) == {"cat": pytest.approx(1.0), "dog": pytest.approx(0.5)}
    assert result.mean_average_precision == pytest.approx(0.75)


def test_class_predicted_but_never_ground_truth_is_not_scored() -> None:
    gt = [[_box(CAT, 0, 0)]]
    pred = [[_box(CAT, 0, 0, confidence=0.9), _box(DOG, 0, 0, confidence=0.9)]]

    result = average_precision.compute(
        gt_per_image=gt, pred_per_image=pred, label_names=LABEL_NAMES, iou_thresholds=[0.5]
    )

    assert _ap_by_label(result) == {"cat": pytest.approx(1.0)}  # dog has no ground truth
    assert result.mean_average_precision == pytest.approx(1.0)


def test_averages_over_iou_thresholds() -> None:
    # IoU 0.6: a true positive at 0.5, a miss at 0.7. AP averages to 0.5.
    gt = [[_box(CAT, 0, 0, width=10, height=10)]]
    pred = [[_box(CAT, 0, 0, width=10, height=6, confidence=0.9)]]

    result = average_precision.compute(
        gt_per_image=gt, pred_per_image=pred, label_names=LABEL_NAMES, iou_thresholds=[0.5, 0.7]
    )

    assert _ap_by_label(result) == {"cat": pytest.approx(0.5)}
    assert result.iou_thresholds == [0.5, 0.7]


def test_ground_truth_with_no_predictions_has_ap_zero() -> None:
    result = average_precision.compute(
        gt_per_image=[[_box(CAT, 0, 0)]],
        pred_per_image=[[]],
        label_names=LABEL_NAMES,
        iou_thresholds=[0.5],
    )

    assert _ap_by_label(result) == {"cat": pytest.approx(0.0)}
    assert result.mean_average_precision == pytest.approx(0.0)


def test_no_ground_truth_at_all() -> None:
    result = average_precision.compute(
        gt_per_image=[[]],
        pred_per_image=[[_box(CAT, 0, 0, confidence=0.9)]],
        label_names=LABEL_NAMES,
        iou_thresholds=[0.5],
    )

    assert result.per_class == []
    assert result.mean_average_precision == pytest.approx(0.0)
