"""Tests for per-class detection average precision."""

from __future__ import annotations

from uuid import UUID, uuid4

import pytest

from lightly_studio.evaluation import average_precision
from lightly_studio.evaluation.average_precision import ClassAveragePrecision
from lightly_studio.evaluation.object_detection_metric import BoundingBox
from lightly_studio.models.evaluation_class_metric import EvaluationClassMetricTable

CAT = uuid4()
DOG = uuid4()
LABEL_NAMES = {CAT: "cat", DOG: "dog"}
RUN_ID = uuid4()


def test_compute__perfect_detection_has_ap_one() -> None:
    gt = [[_box(label_id=CAT, x=0, y=0)]]
    pred = [[_box(label_id=CAT, x=0, y=0, confidence=0.9)]]

    results = average_precision.compute(gt_per_image=gt, pred_per_image=pred, iou_thresholds=[0.5])

    assert _ap_by_label_and_threshold(results=results) == {("cat", 0.5): pytest.approx(1.0)}


def test_compute__high_confidence_false_positive_halves_ap() -> None:
    # One ground truth. A high-confidence prediction misses, a lower one hits.
    gt = [[_box(label_id=CAT, x=0, y=0)]]
    pred = [
        [
            _box(label_id=CAT, x=500, y=500, confidence=0.9),
            _box(label_id=CAT, x=0, y=0, confidence=0.8),
        ]
    ]

    results = average_precision.compute(gt_per_image=gt, pred_per_image=pred, iou_thresholds=[0.5])

    # Precision is 0.5 across the recall range, so 101-point AP is 0.5.
    assert _ap_by_label_and_threshold(results=results) == {("cat", 0.5): pytest.approx(0.5)}


def test_compute__per_class_values() -> None:
    gt = [[_box(label_id=CAT, x=0, y=0), _box(label_id=DOG, x=0, y=0)]]
    pred = [
        [
            _box(label_id=CAT, x=0, y=0, confidence=0.9),  # cat true positive -> AP 1.0
            _box(label_id=DOG, x=500, y=500, confidence=0.9),  # dog false positive
            _box(label_id=DOG, x=0, y=0, confidence=0.8),  # dog true positive -> AP 0.5
        ]
    ]

    results = average_precision.compute(gt_per_image=gt, pred_per_image=pred, iou_thresholds=[0.5])

    assert _ap_by_label_and_threshold(results=results) == {
        ("cat", 0.5): pytest.approx(1.0),
        ("dog", 0.5): pytest.approx(0.5),
    }


def test_compute__predictions_match_only_their_own_class() -> None:
    # A dog prediction on the cat ground truth does not count for the cat.
    gt = [[_box(label_id=CAT, x=0, y=0)]]
    pred = [[_box(label_id=DOG, x=0, y=0, confidence=0.9)]]

    results = average_precision.compute(gt_per_image=gt, pred_per_image=pred, iou_thresholds=[0.5])

    assert _ap_by_label_and_threshold(results=results) == {("cat", 0.5): pytest.approx(0.0)}


def test_compute__class_predicted_but_never_ground_truth_is_not_scored() -> None:
    gt = [[_box(label_id=CAT, x=0, y=0)]]
    pred = [
        [
            _box(label_id=CAT, x=0, y=0, confidence=0.9),
            _box(label_id=DOG, x=0, y=0, confidence=0.9),
        ]
    ]

    results = average_precision.compute(gt_per_image=gt, pred_per_image=pred, iou_thresholds=[0.5])

    assert _ap_by_label_and_threshold(results=results) == {("cat", 0.5): pytest.approx(1.0)}


def test_compute__value_per_iou_threshold() -> None:
    # IoU 0.6: a true positive at 0.5, a miss at 0.7.
    gt = [[_box(label_id=CAT, x=0, y=0, width=10, height=10)]]
    pred = [[_box(label_id=CAT, x=0, y=0, width=10, height=6, confidence=0.9)]]

    results = average_precision.compute(
        gt_per_image=gt, pred_per_image=pred, iou_thresholds=[0.5, 0.7]
    )

    assert _ap_by_label_and_threshold(results=results) == {
        ("cat", 0.5): pytest.approx(1.0),
        ("cat", 0.7): pytest.approx(0.0),
    }


def test_compute__rematches_at_each_iou_threshold() -> None:
    # At IoU 0.5 the confident box (IoU 0.82) takes the ground truth and the exact
    # duplicate is a false positive. At IoU 0.85 the confident box misses, so the
    # duplicate becomes the match.
    gt = [[_box(label_id=CAT, x=0, y=0, width=100, height=100)]]
    pred = [
        [
            _box(label_id=CAT, x=5, y=5, width=100, height=100, confidence=0.9),
            _box(label_id=CAT, x=0, y=0, width=100, height=100, confidence=0.6),
        ]
    ]

    results = average_precision.compute(
        gt_per_image=gt, pred_per_image=pred, iou_thresholds=[0.5, 0.85]
    )

    assert _ap_by_label_and_threshold(results=results) == {
        ("cat", 0.5): pytest.approx(1.0),
        ("cat", 0.85): pytest.approx(0.5),
    }


def test_compute__ground_truth_with_no_predictions_has_ap_zero() -> None:
    results = average_precision.compute(
        gt_per_image=[[_box(label_id=CAT, x=0, y=0)]],
        pred_per_image=[[]],
        iou_thresholds=[0.5],
    )

    assert _ap_by_label_and_threshold(results=results) == {("cat", 0.5): pytest.approx(0.0)}


def test_compute__no_ground_truth_at_all() -> None:
    results = average_precision.compute(
        gt_per_image=[[]],
        pred_per_image=[[_box(label_id=CAT, x=0, y=0, confidence=0.9)]],
        iou_thresholds=[0.5],
    )

    assert results == []


def test_compute__sorted_by_label_id_and_threshold() -> None:
    gt = [[_box(label_id=DOG, x=0, y=0), _box(label_id=CAT, x=0, y=0)]]

    results = average_precision.compute(
        gt_per_image=gt, pred_per_image=[[]], iou_thresholds=[0.7, 0.5]
    )

    first, second = sorted([CAT, DOG], key=str)
    assert [(result.label_id, result.iou_threshold) for result in results] == [
        (first, 0.5),
        (first, 0.7),
        (second, 0.5),
        (second, 0.7),
    ]


@pytest.mark.parametrize(
    ("iou_threshold", "run_classwise", "expected"),
    [
        (0.5, True, {}),
        (0.75, True, {"iou_threshold": 0.75}),
        (0.5, False, {"classwise": True}),
        (0.75, False, {"iou_threshold": 0.75, "classwise": True}),
    ],
)
def test_config_override(
    iou_threshold: float, run_classwise: bool, expected: dict[str, object]
) -> None:
    assert (
        average_precision.config_override(
            iou_threshold=iou_threshold, run_iou_threshold=0.5, run_classwise=run_classwise
        )
        == expected
    )


def test_by_label_and_threshold() -> None:
    rows = [
        *(
            _class_metric(label_id=label_id, iou_threshold=threshold, value=value)
            for label_id, value in ((CAT, 0.8), (DOG, 0.2))
            for threshold in (0.5, 0.75)
        ),
        EvaluationClassMetricTable(
            evaluation_run_id=RUN_ID, annotation_label_id=CAT, metric_name="iou", value=0.3
        ),
    ]

    grouped = average_precision.by_label_and_threshold(
        class_metrics=rows, run_config={"iou_threshold": 0.5, "classwise": True}
    )

    # Rows of other metrics, such as "iou", are ignored.
    assert grouped == {CAT: {0.5: 0.8, 0.75: 0.8}, DOG: {0.5: 0.2, 0.75: 0.2}}


def test_by_label_and_threshold__row_without_override_has_the_run_threshold() -> None:
    rows = [
        EvaluationClassMetricTable(
            evaluation_run_id=RUN_ID,
            annotation_label_id=CAT,
            metric_name=average_precision.METRIC_NAME,
            config_override={},
            value=0.7,
        )
    ]

    grouped = average_precision.by_label_and_threshold(
        class_metrics=rows, run_config={"iou_threshold": 0.75, "classwise": True}
    )

    assert grouped == {CAT: {0.75: 0.7}}


def test_by_label_and_threshold__no_rows() -> None:
    assert (
        average_precision.by_label_and_threshold(
            class_metrics=[], run_config={"iou_threshold": 0.5, "classwise": True}
        )
        == {}
    )


def test_coco_iou_thresholds() -> None:
    assert average_precision.COCO_IOU_THRESHOLDS == [
        0.5,
        0.55,
        0.6,
        0.65,
        0.7,
        0.75,
        0.8,
        0.85,
        0.9,
        0.95,
    ]


def test_compute__at_most_100_predictions_per_image_and_class() -> None:
    # 200 separate ground truths, each with an exact prediction. Only the 100 predictions
    # with the highest confidence are scored, so recall stops at 0.5: AP is 51/101.
    positions = [(30 * (index % 20), 30 * (index // 20)) for index in range(200)]
    gt = [[_box(label_id=CAT, x=x, y=y) for x, y in positions]]
    pred = [
        [
            _box(label_id=CAT, x=x, y=y, confidence=1.0 - 0.001 * index)
            for index, (x, y) in enumerate(positions)
        ]
    ]

    results = average_precision.compute(gt_per_image=gt, pred_per_image=pred, iou_thresholds=[0.5])

    assert _ap_by_label_and_threshold(results=results) == {("cat", 0.5): pytest.approx(51 / 101)}


def test_compute__keeps_the_predictions_with_the_highest_confidence() -> None:
    # 100 low-confidence false positives come before one high-confidence true positive.
    # Only the cap after sorting by confidence keeps the true positive, so AP is 1.0.
    gt = [[_box(label_id=CAT, x=0, y=0)]]
    false_positives = [
        _box(label_id=CAT, x=30 * (index % 10), y=100 + 30 * (index // 10), confidence=0.1)
        for index in range(100)
    ]
    pred = [[*false_positives, _box(label_id=CAT, x=0, y=0, confidence=0.9)]]

    results = average_precision.compute(gt_per_image=gt, pred_per_image=pred, iou_thresholds=[0.5])

    assert _ap_by_label_and_threshold(results=results) == {("cat", 0.5): pytest.approx(1.0)}


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


def _ap_by_label_and_threshold(
    results: list[ClassAveragePrecision],
) -> dict[tuple[str, float], float]:
    return {
        (LABEL_NAMES[result.label_id], result.iou_threshold): result.average_precision
        for result in results
    }


def _class_metric(label_id: UUID, iou_threshold: float, value: float) -> EvaluationClassMetricTable:
    return EvaluationClassMetricTable(
        evaluation_run_id=RUN_ID,
        annotation_label_id=label_id,
        metric_name=average_precision.METRIC_NAME,
        config_override=average_precision.config_override(
            iou_threshold=iou_threshold, run_iou_threshold=0.5, run_classwise=True
        ),
        value=value,
    )
