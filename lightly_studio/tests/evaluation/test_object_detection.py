"""Tests for object detection evaluation primitives."""

from __future__ import annotations

from uuid import uuid4

import numpy as np
import pytest

from lightly_studio.evaluation import object_detection_metric
from lightly_studio.evaluation.object_detection_metric import BoundingBox


def test_match_with_iou_matrix__wrong_iou_matrix_shape() -> None:
    pred_id = uuid4()
    gt_id = uuid4()
    label_id = uuid4()
    preds = [
        BoundingBox(
            annotation_id=pred_id,
            x=0,
            y=0,
            width=10,
            height=10,
            label_id=label_id,
            confidence=0.9,
        )
    ]
    gts = [
        BoundingBox(annotation_id=gt_id, x=0, y=0, width=10, height=10, label_id=label_id),
        BoundingBox(annotation_id=uuid4(), x=20, y=0, width=10, height=10, label_id=label_id),
    ]
    iou_matrix = np.array([[1.0]])
    with pytest.raises(ValueError, match="iou_matrix shape"):
        object_detection_metric.match_with_iou_matrix(
            predictions=preds,
            ground_truths=gts,
            iou_matrix=iou_matrix,
            iou_threshold=0.5,
        )


def test_match_with_iou_matrix__no_preds_no_gts() -> None:
    result = object_detection_metric.match_with_iou_matrix(
        predictions=[],
        ground_truths=[],
        iou_matrix=np.empty((0, 0)),
        iou_threshold=0.5,
    )
    assert result.tp == 0
    assert result.fp == 0
    assert result.fn == 0


def test_match_with_iou_matrix__no_preds() -> None:
    gt_id = uuid4()
    label_id = uuid4()
    gts = [BoundingBox(annotation_id=gt_id, x=0, y=0, width=10, height=10, label_id=label_id)]
    result = object_detection_metric.match_with_iou_matrix(
        predictions=[],
        ground_truths=gts,
        iou_matrix=np.empty((0, 1)),
        iou_threshold=0.5,
    )
    assert result.tp == 0
    assert result.fp == 0
    assert result.fn == 1
    assert result.unmatched_gt_ids == [gt_id]


def test_match_with_iou_matrix__no_gts() -> None:
    pred_id = uuid4()
    label_id = uuid4()
    preds = [
        BoundingBox(
            annotation_id=pred_id,
            x=0,
            y=0,
            width=10,
            height=10,
            label_id=label_id,
            confidence=0.9,
        )
    ]
    result = object_detection_metric.match_with_iou_matrix(
        predictions=preds,
        ground_truths=[],
        iou_matrix=np.empty((1, 0)),
        iou_threshold=0.5,
    )
    assert result.tp == 0
    assert result.fp == 1
    assert result.fn == 0
    assert result.unmatched_prediction_ids == [pred_id]


def test_match_with_iou_matrix__greedy_match_by_confidence() -> None:
    pred_high_id = uuid4()
    pred_low_id = uuid4()
    gt_id = uuid4()
    label_id = uuid4()
    preds = [
        BoundingBox(
            annotation_id=pred_high_id,
            x=0,
            y=0,
            width=10,
            height=10,
            label_id=label_id,
            confidence=0.9,
        ),
        BoundingBox(
            annotation_id=pred_low_id,
            x=0,
            y=0,
            width=10,
            height=10,
            label_id=label_id,
            confidence=0.4,
        ),
    ]
    gts = [BoundingBox(annotation_id=gt_id, x=0, y=0, width=10, height=10, label_id=label_id)]
    iou_matrix = np.array([[1.0], [1.0]])
    result = object_detection_metric.match_with_iou_matrix(
        predictions=preds,
        ground_truths=gts,
        iou_matrix=iou_matrix,
        iou_threshold=0.5,
    )
    assert result.tp == 1
    assert result.fp == 1
    assert result.fn == 0
    assert result.matches[0].pred_id == pred_high_id
    assert result.unmatched_prediction_ids == [pred_low_id]


def test_match_with_iou_matrix__multiple_preds_multiple_gts() -> None:
    pred_high_id = uuid4()
    pred_mid_id = uuid4()
    pred_low_id = uuid4()
    gt_first_id = uuid4()
    gt_second_id = uuid4()
    label_id = uuid4()
    preds = [
        BoundingBox(
            annotation_id=pred_high_id,
            x=0,
            y=0,
            width=10,
            height=10,
            label_id=label_id,
            confidence=0.9,
        ),
        BoundingBox(
            annotation_id=pred_mid_id,
            x=20,
            y=0,
            width=10,
            height=10,
            label_id=label_id,
            confidence=0.8,
        ),
        BoundingBox(
            annotation_id=pred_low_id,
            x=40,
            y=0,
            width=10,
            height=10,
            label_id=label_id,
            confidence=0.7,
        ),
    ]
    gts = [
        BoundingBox(annotation_id=gt_first_id, x=0, y=0, width=10, height=10, label_id=label_id),
        BoundingBox(annotation_id=gt_second_id, x=20, y=0, width=10, height=10, label_id=label_id),
    ]
    iou_matrix = np.array(
        [
            [0.5, 0.0],
            [0.0, 0.5],
            [0.3, 0.3],
        ]
    )
    result = object_detection_metric.match_with_iou_matrix(
        predictions=preds,
        ground_truths=gts,
        iou_matrix=iou_matrix,
        iou_threshold=0.5,
    )
    assert result.tp == 2
    assert result.fp == 1
    assert result.fn == 0
    assert result.matches[0].pred_id == pred_high_id
    assert result.matches[1].pred_id == pred_mid_id
    assert result.matches[0].gt_id == gt_first_id
    assert result.matches[1].gt_id == gt_second_id
    assert result.matches[0].iou == pytest.approx(0.5)
    assert result.matches[1].iou == pytest.approx(0.5)
    assert result.unmatched_prediction_ids == [pred_low_id]


def test_match_with_iou_matrix__equal_confidence_uses_list_order() -> None:
    """Predictions with equal confidence are matched in list order (first wins)."""
    pred_first_id = uuid4()
    pred_second_id = uuid4()
    gt_id = uuid4()
    label_id = uuid4()
    preds = [
        BoundingBox(
            annotation_id=pred_first_id,
            x=0,
            y=0,
            width=10,
            height=10,
            label_id=label_id,
            confidence=0.8,
        ),
        BoundingBox(
            annotation_id=pred_second_id,
            x=0,
            y=0,
            width=10,
            height=10,
            label_id=label_id,
            confidence=0.8,
        ),
    ]
    gts = [BoundingBox(annotation_id=gt_id, x=0, y=0, width=10, height=10, label_id=label_id)]
    iou_matrix = np.array([[1.0], [1.0]])
    result = object_detection_metric.match_with_iou_matrix(
        predictions=preds,
        ground_truths=gts,
        iou_matrix=iou_matrix,
        iou_threshold=0.5,
    )
    assert result.tp == 1
    assert result.fp == 1
    assert result.matches[0].pred_id == pred_first_id
    assert result.unmatched_prediction_ids == [pred_second_id]


def test_match_with_iou_matrix__pred_without_confidence_treated_as_zero() -> None:
    pred_with_conf_id = uuid4()
    pred_no_conf_id = uuid4()
    gt_id = uuid4()
    label_id = uuid4()
    preds = [
        BoundingBox(
            annotation_id=pred_no_conf_id,
            x=0,
            y=0,
            width=10,
            height=10,
            label_id=label_id,
            confidence=None,
        ),
        BoundingBox(
            annotation_id=pred_with_conf_id,
            x=0,
            y=0,
            width=10,
            height=10,
            label_id=label_id,
            confidence=0.9,
        ),
    ]
    gts = [BoundingBox(annotation_id=gt_id, x=0, y=0, width=10, height=10, label_id=label_id)]
    iou_matrix = np.array([[1.0], [1.0]])
    result = object_detection_metric.match_with_iou_matrix(
        predictions=preds,
        ground_truths=gts,
        iou_matrix=iou_matrix,
        iou_threshold=0.5,
    )
    assert result.tp == 1
    assert result.matches[0].pred_id == pred_with_conf_id


def test_match_with_iou_matrix__all_preds_below_threshold() -> None:
    pred_first_id = uuid4()
    pred_second_id = uuid4()
    gt_first_id = uuid4()
    gt_second_id = uuid4()
    label_id = uuid4()
    preds = [
        BoundingBox(
            annotation_id=pred_first_id,
            x=0,
            y=0,
            width=10,
            height=10,
            label_id=label_id,
            confidence=0.9,
        ),
        BoundingBox(
            annotation_id=pred_second_id,
            x=20,
            y=0,
            width=10,
            height=10,
            label_id=label_id,
            confidence=0.8,
        ),
    ]
    gts = [
        BoundingBox(annotation_id=gt_first_id, x=0, y=0, width=10, height=10, label_id=label_id),
        BoundingBox(annotation_id=gt_second_id, x=20, y=0, width=10, height=10, label_id=label_id),
    ]
    iou_matrix = np.array(
        [
            [0.4, 0.1],
            [0.1, 0.3],
        ]
    )
    result = object_detection_metric.match_with_iou_matrix(
        predictions=preds,
        ground_truths=gts,
        iou_matrix=iou_matrix,
        iou_threshold=0.5,
    )
    assert result.tp == 0
    assert result.fp == 2
    assert result.fn == 2
    assert set(result.unmatched_prediction_ids) == {pred_first_id, pred_second_id}
    assert set(result.unmatched_gt_ids) == {gt_first_id, gt_second_id}


def test_compute_iou_matrix__empty_predictions() -> None:
    result = object_detection_metric.compute_iou_matrix(
        pred_corners=np.empty((0, 4), dtype=np.int64),
        gt_corners=np.array([[0, 0, 10, 10]]),
    )
    assert result.shape == (0, 1)


def test_compute_iou_matrix__empty_ground_truths() -> None:
    result = object_detection_metric.compute_iou_matrix(
        pred_corners=np.array([[0, 0, 10, 10]]),
        gt_corners=np.empty((0, 4), dtype=np.int64),
    )
    assert result.shape == (1, 0)


def test_compute_iou_matrix__perfect_overlap() -> None:
    box = np.array([[0, 0, 10, 10]])
    result = object_detection_metric.compute_iou_matrix(pred_corners=box, gt_corners=box)
    assert result[0, 0] == pytest.approx(1.0)


def test_compute_iou_matrix__no_overlap() -> None:
    pred = np.array([[0, 0, 10, 10]])
    gt = np.array([[20, 0, 30, 10]])
    result = object_detection_metric.compute_iou_matrix(pred_corners=pred, gt_corners=gt)
    assert result[0, 0] == pytest.approx(0.0)


def test_compute_iou_matrix__touching_boxes_have_zero_iou() -> None:
    # Boxes share an edge but have no area in common.
    pred = np.array([[0, 0, 10, 10]])
    gt = np.array([[10, 0, 20, 10]])
    result = object_detection_metric.compute_iou_matrix(pred_corners=pred, gt_corners=gt)
    assert result[0, 0] == pytest.approx(0.0)


def test_compute_iou_matrix__known_partial_overlap() -> None:
    # pred [0,0,10,10] and gt [5,0,15,10]: intersection=50, union=150 → IoU=1/3.
    pred = np.array([[0, 0, 10, 10]])
    gt = np.array([[5, 0, 15, 10]])
    result = object_detection_metric.compute_iou_matrix(pred_corners=pred, gt_corners=gt)
    assert result[0, 0] == pytest.approx(1.0 / 3.0)


def test_compute_iou_matrix__output_shape() -> None:
    predictions = np.array([[0, 0, 10, 10], [20, 0, 30, 10], [40, 0, 50, 10]])
    gts = np.array([[0, 0, 10, 10], [20, 0, 30, 10]])
    result = object_detection_metric.compute_iou_matrix(pred_corners=predictions, gt_corners=gts)
    assert result.shape == (3, 2)


def test_compute_iou_matrix__symmetry() -> None:
    pred = np.array([[0, 0, 10, 10]])
    gt = np.array([[5, 5, 15, 15]])
    assert object_detection_metric.compute_iou_matrix(pred_corners=pred, gt_corners=gt)[
        0, 0
    ] == pytest.approx(
        object_detection_metric.compute_iou_matrix(pred_corners=gt, gt_corners=pred)[0, 0]
    )


def test_compute_iou_matrix__degenerate_point_box_vs_normal_box() -> None:
    """A zero-area point box should have IoU 0 with a normal box, not NaN."""
    pred = np.array([[5, 5, 5, 5]])  # zero-area point
    gt = np.array([[0, 0, 10, 10]])
    result = object_detection_metric.compute_iou_matrix(pred_corners=pred, gt_corners=gt)
    assert not np.isnan(result[0, 0])
    assert result[0, 0] == pytest.approx(0.0)


def test_compute_iou_matrix__both_degenerate_point_boxes() -> None:
    """Two zero-area point boxes should produce IoU 0, not NaN."""
    pred = np.array([[5, 5, 5, 5]])
    gt = np.array([[5, 5, 5, 5]])
    result = object_detection_metric.compute_iou_matrix(pred_corners=pred, gt_corners=gt)
    assert not np.isnan(result[0, 0])
    assert result[0, 0] == pytest.approx(0.0)


def test_compute_iou_matrix__negative_coordinates() -> None:
    """Boxes with negative coordinates should compute IoU correctly."""
    pred = np.array([[-3, -1, 20, 20]])
    gt = np.array([[0, 0, 10, 10]])
    # pred area = 23*21 = 483, gt area = 100, intersection = [0,0,10,10] = 100
    # union = 483 + 100 - 100 = 483, IoU = 100/483
    result = object_detection_metric.compute_iou_matrix(pred_corners=pred, gt_corners=gt)
    assert result[0, 0] == pytest.approx(100.0 / 483.0)


# --- match_image tests ---


def test_match_image__no_preds_no_gts() -> None:
    result = object_detection_metric.match_image(
        predictions=[],
        ground_truths=[],
        iou_threshold=0.5,
        classwise=False,
    )
    assert result.tp == 0
    assert result.fp == 0
    assert result.fn == 0


def test_match_image__single_class_perfect_match() -> None:
    pred_id = uuid4()
    gt_id = uuid4()
    label_id = uuid4()
    preds = [
        BoundingBox(
            annotation_id=pred_id,
            x=0,
            y=0,
            width=10,
            height=10,
            label_id=label_id,
            confidence=0.9,
        )
    ]
    gts = [BoundingBox(annotation_id=gt_id, x=0, y=0, width=10, height=10, label_id=label_id)]
    result = object_detection_metric.match_image(
        predictions=preds,
        ground_truths=gts,
        iou_threshold=0.5,
        classwise=False,
    )
    assert result.tp == 1
    assert result.fp == 0
    assert result.fn == 0
    assert result.matches[0].pred_id == pred_id
    assert result.matches[0].gt_id == gt_id


def test_match_image__classwise_same_class_as_non_classwise() -> None:
    """When all boxes share the same label, classwise and non-classwise should be identical."""
    pred_id = uuid4()
    gt_id = uuid4()
    label_id = uuid4()
    preds = [
        BoundingBox(
            annotation_id=pred_id,
            x=0,
            y=0,
            width=10,
            height=10,
            label_id=label_id,
            confidence=0.9,
        )
    ]
    gts = [BoundingBox(annotation_id=gt_id, x=0, y=0, width=10, height=10, label_id=label_id)]
    result_classwise = object_detection_metric.match_image(
        predictions=preds,
        ground_truths=gts,
        iou_threshold=0.5,
        classwise=True,
    )
    result_non_classwise = object_detection_metric.match_image(
        predictions=preds,
        ground_truths=gts,
        iou_threshold=0.5,
        classwise=False,
    )
    assert result_classwise.tp == result_non_classwise.tp
    assert result_classwise.fp == result_non_classwise.fp
    assert result_classwise.fn == result_non_classwise.fn
    assert result_classwise.matches[0].pred_id == result_non_classwise.matches[0].pred_id
    assert result_classwise.matches[0].gt_id == result_non_classwise.matches[0].gt_id


def test_match_image__classwise_prevents_cross_class_match() -> None:
    """A prediction with a different label than the GT should not match when classwise=True."""
    pred_id = uuid4()
    gt_id = uuid4()
    pred_label = uuid4()
    gt_label = uuid4()
    preds = [
        BoundingBox(
            annotation_id=pred_id,
            x=0,
            y=0,
            width=10,
            height=10,
            label_id=pred_label,
            confidence=0.9,
        )
    ]
    gts = [BoundingBox(annotation_id=gt_id, x=0, y=0, width=10, height=10, label_id=gt_label)]
    result_classwise = object_detection_metric.match_image(
        predictions=preds,
        ground_truths=gts,
        iou_threshold=0.5,
        classwise=True,
    )
    assert result_classwise.tp == 0
    assert result_classwise.fp == 1
    assert result_classwise.fn == 1
    assert result_classwise.unmatched_prediction_ids == [pred_id]
    assert result_classwise.unmatched_gt_ids == [gt_id]


def test_match_image__non_classwise_allows_cross_class_match() -> None:
    """A prediction with a different label than the GT should match when classwise=False."""
    pred_id = uuid4()
    gt_id = uuid4()
    pred_label = uuid4()
    gt_label = uuid4()
    preds = [
        BoundingBox(
            annotation_id=pred_id,
            x=0,
            y=0,
            width=10,
            height=10,
            label_id=pred_label,
            confidence=0.9,
        )
    ]
    gts = [BoundingBox(annotation_id=gt_id, x=0, y=0, width=10, height=10, label_id=gt_label)]
    result_non_classwise = object_detection_metric.match_image(
        predictions=preds,
        ground_truths=gts,
        iou_threshold=0.5,
        classwise=False,
    )
    assert result_non_classwise.tp == 1
    assert result_non_classwise.fp == 0
    assert result_non_classwise.fn == 0
    assert result_non_classwise.matches[0].pred_id == pred_id
    assert result_non_classwise.matches[0].gt_id == gt_id


def test_match_image__classwise_multiple_classes() -> None:
    """Classwise matching should match within each class independently."""
    pred_a_id = uuid4()
    pred_b_id = uuid4()
    gt_a_id = uuid4()
    gt_b_id = uuid4()
    label_a = uuid4()
    label_b = uuid4()
    preds = [
        BoundingBox(
            annotation_id=pred_a_id,
            x=0,
            y=0,
            width=10,
            height=10,
            label_id=label_a,
            confidence=0.9,
        ),
        BoundingBox(
            annotation_id=pred_b_id,
            x=20,
            y=0,
            width=10,
            height=10,
            label_id=label_b,
            confidence=0.8,
        ),
    ]
    gts = [
        BoundingBox(annotation_id=gt_a_id, x=0, y=0, width=10, height=10, label_id=label_a),
        BoundingBox(annotation_id=gt_b_id, x=20, y=0, width=10, height=10, label_id=label_b),
    ]
    result = object_detection_metric.match_image(
        predictions=preds,
        ground_truths=gts,
        iou_threshold=0.5,
        classwise=True,
    )
    assert result.tp == 2
    assert result.fp == 0
    assert result.fn == 0
    match_ids = {m.pred_id: m.gt_id for m in result.matches}
    assert match_ids[pred_a_id] == gt_a_id
    assert match_ids[pred_b_id] == gt_b_id


def test_match_image__classwise_wrong_class_no_match_even_with_overlap() -> None:
    """Overlapping boxes with different classes should not match in classwise mode."""
    pred_a_id = uuid4()
    gt_b_id = uuid4()
    label_a = uuid4()
    label_b = uuid4()
    preds = [
        BoundingBox(
            annotation_id=pred_a_id,
            x=0,
            y=0,
            width=10,
            height=10,
            label_id=label_a,
            confidence=0.9,
        )
    ]
    gts = [BoundingBox(annotation_id=gt_b_id, x=0, y=0, width=10, height=10, label_id=label_b)]
    result = object_detection_metric.match_image(
        predictions=preds,
        ground_truths=gts,
        iou_threshold=0.5,
        classwise=True,
    )
    assert result.tp == 0
    assert result.fp == 1
    assert result.fn == 1


def test_match_image__classwise_partial_match_one_class() -> None:
    """Only one class has matching boxes; the other class has no predictions."""
    pred_a_id = uuid4()
    gt_a_id = uuid4()
    gt_b_id = uuid4()
    label_a = uuid4()
    label_b = uuid4()
    preds = [
        BoundingBox(
            annotation_id=pred_a_id,
            x=0,
            y=0,
            width=10,
            height=10,
            label_id=label_a,
            confidence=0.9,
        )
    ]
    gts = [
        BoundingBox(annotation_id=gt_a_id, x=0, y=0, width=10, height=10, label_id=label_a),
        BoundingBox(annotation_id=gt_b_id, x=20, y=0, width=10, height=10, label_id=label_b),
    ]
    result = object_detection_metric.match_image(
        predictions=preds,
        ground_truths=gts,
        iou_threshold=0.5,
        classwise=True,
    )
    assert result.tp == 1
    assert result.fp == 0
    assert result.fn == 1
    assert result.matches[0].pred_id == pred_a_id
    assert result.matches[0].gt_id == gt_a_id
    assert result.unmatched_gt_ids == [gt_b_id]


def test_match_image__classwise_prediction_has_no_gt_class() -> None:
    """A prediction for a class not present in GTs should be FP."""
    pred_a_id = uuid4()
    gt_b_id = uuid4()
    label_a = uuid4()
    label_b = uuid4()
    preds = [
        BoundingBox(
            annotation_id=pred_a_id,
            x=0,
            y=0,
            width=10,
            height=10,
            label_id=label_a,
            confidence=0.9,
        )
    ]
    gts = [BoundingBox(annotation_id=gt_b_id, x=20, y=0, width=10, height=10, label_id=label_b)]
    result = object_detection_metric.match_image(
        predictions=preds,
        ground_truths=gts,
        iou_threshold=0.5,
        classwise=True,
    )
    assert result.tp == 0
    assert result.fp == 1
    assert result.fn == 1
    assert result.unmatched_prediction_ids == [pred_a_id]
    assert result.unmatched_gt_ids == [gt_b_id]
