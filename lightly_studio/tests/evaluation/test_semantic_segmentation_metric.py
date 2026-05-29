"""Tests for semantic segmentation evaluation metric primitives."""

from __future__ import annotations

from uuid import uuid4

import numpy as np
import pytest

from lightly_studio.evaluation import semantic_segmentation_metric


def test_compute_iou__perfect_overlap() -> None:
    mask = np.array([[1, 1], [0, 0]], dtype=np.bool_)
    assert semantic_segmentation_metric.compute_iou(gt_mask=mask, pred_mask=mask) == pytest.approx(
        1.0
    )


def test_compute_iou__no_overlap() -> None:
    gt_mask = np.array([[1, 0], [0, 0]], dtype=np.bool_)
    pred_mask = np.array([[0, 0], [0, 1]], dtype=np.bool_)
    assert semantic_segmentation_metric.compute_iou(
        gt_mask=gt_mask, pred_mask=pred_mask
    ) == pytest.approx(0.0)


def test_compute_iou__partial_overlap() -> None:
    gt_mask = np.array([[1, 1], [0, 0]], dtype=np.bool_)
    pred_mask = np.array([[1, 0], [0, 0]], dtype=np.bool_)
    assert semantic_segmentation_metric.compute_iou(
        gt_mask=gt_mask, pred_mask=pred_mask
    ) == pytest.approx(1 / 2)


def test_compute_iou__both_empty() -> None:
    mask = np.zeros((2, 2), dtype=np.bool_)
    assert semantic_segmentation_metric.compute_iou(gt_mask=mask, pred_mask=mask) == pytest.approx(
        1.0
    )


def test_compute_class_ious__equal_weight_mean() -> None:
    label_a = uuid4()
    label_b = uuid4()
    gt_masks = {
        label_a: np.array([[1, 0], [0, 0]], dtype=np.bool_),
        label_b: np.array([[0, 0], [0, 0]], dtype=np.bool_),
    }
    pred_masks = {
        label_a: np.array([[1, 0], [0, 0]], dtype=np.bool_),
        label_b: np.array([[0, 1], [0, 0]], dtype=np.bool_),
    }

    class_ious = semantic_segmentation_metric.compute_class_ious(
        gt_masks=gt_masks,
        pred_masks=pred_masks,
    )

    assert class_ious[label_a] == pytest.approx(1.0)
    assert class_ious[label_b] == pytest.approx(0.0)
    assert np.mean(list(class_ious.values())) == pytest.approx(0.5)


def test_compute_class_ious__class_only_in_predictions() -> None:
    label_id = uuid4()
    class_ious = semantic_segmentation_metric.compute_class_ious(
        gt_masks={},
        pred_masks={label_id: np.array([[1, 0], [0, 0]], dtype=np.bool_)},
    )
    assert class_ious[label_id] == pytest.approx(0.0)
