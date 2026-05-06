"""Tests for object detection evaluation primitives."""

from __future__ import annotations

import numpy as np
import pytest

from lightly_studio.evaluation import object_detection_metric


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
