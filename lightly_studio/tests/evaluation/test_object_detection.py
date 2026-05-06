"""Tests for object detection evaluation primitives."""

from __future__ import annotations

import numpy as np
import pytest

from lightly_studio.evaluation import object_detection_metric


class TestComputeIouMatrix:
    def test_empty_predictions(self) -> None:
        result = object_detection_metric.compute_iou_matrix(
            np.empty((0, 4)), np.array([[0.0, 0.0, 10.0, 10.0]])
        )
        assert result.shape == (0, 1)

    def test_empty_ground_truths(self) -> None:
        result = object_detection_metric.compute_iou_matrix(
            np.array([[0.0, 0.0, 10.0, 10.0]]), np.empty((0, 4))
        )
        assert result.shape == (1, 0)

    def test_perfect_overlap(self) -> None:
        box = np.array([[0.0, 0.0, 10.0, 10.0]])
        result = object_detection_metric.compute_iou_matrix(box, box)
        assert result[0, 0] == pytest.approx(1.0)

    def test_no_overlap(self) -> None:
        pred = np.array([[0.0, 0.0, 10.0, 10.0]])
        gt = np.array([[20.0, 0.0, 30.0, 10.0]])
        result = object_detection_metric.compute_iou_matrix(pred, gt)
        assert result[0, 0] == pytest.approx(0.0)

    def test_touching_boxes_have_zero_iou(self) -> None:
        # Boxes share an edge but have no area in common.
        pred = np.array([[0.0, 0.0, 10.0, 10.0]])
        gt = np.array([[10.0, 0.0, 20.0, 10.0]])
        result = object_detection_metric.compute_iou_matrix(pred, gt)
        assert result[0, 0] == pytest.approx(0.0)

    def test_known_partial_overlap(self) -> None:
        # pred [0,0,10,10] and gt [5,0,15,10]: intersection=50, union=150 → IoU=1/3.
        pred = np.array([[0.0, 0.0, 10.0, 10.0]])
        gt = np.array([[5.0, 0.0, 15.0, 10.0]])
        result = object_detection_metric.compute_iou_matrix(pred, gt)
        assert result[0, 0] == pytest.approx(1.0 / 3.0)

    def test_output_shape(self) -> None:
        predictions = np.array([[float(i * 20), 0.0, float(i * 20 + 10), 10.0] for i in range(3)])
        gts = np.array([[float(i * 20), 0.0, float(i * 20 + 10), 10.0] for i in range(2)])
        result = object_detection_metric.compute_iou_matrix(predictions, gts)
        assert result.shape == (3, 2)

    def test_symmetry(self) -> None:
        pred = np.array([[0.0, 0.0, 10.0, 10.0]])
        gt = np.array([[5.0, 5.0, 15.0, 15.0]])
        assert object_detection_metric.compute_iou_matrix(pred, gt)[0, 0] == pytest.approx(
            object_detection_metric.compute_iou_matrix(gt, pred)[0, 0]
        )
