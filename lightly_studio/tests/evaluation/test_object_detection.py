"""Tests for object detection evaluation primitives."""

from __future__ import annotations

from uuid import uuid4

import numpy as np
import pytest

from lightly_studio.evaluation import object_detection_metric
from lightly_studio.evaluation.object_detection_metric import BoundingBox


class TestMatchWithIouMatrix:
    def test_no_preds_no_gts(self) -> None:
        sample_id = uuid4()
        result = object_detection_metric.match_with_iou_matrix(
            sample_id=sample_id,
            predictions=[],
            ground_truths=[],
            iou_matrix=np.empty((0, 0)),
            iou_threshold=0.5,
        )
        assert result.sample_id == sample_id
        assert result.tp == 0
        assert result.fp == 0
        assert result.fn == 0

    def test_no_preds(self) -> None:
        sample_id = uuid4()
        gt_id = uuid4()
        gts = [BoundingBox(annotation_id=gt_id, x=0, y=0, width=10, height=10, label_id=uuid4())]
        result = object_detection_metric.match_with_iou_matrix(
            sample_id=sample_id,
            predictions=[],
            ground_truths=gts,
            iou_matrix=np.empty((0, 1)),
            iou_threshold=0.5,
        )
        assert result.tp == 0
        assert result.fp == 0
        assert result.fn == 1
        assert result.unmatched_gt_ids == [gt_id]

    def test_no_gts(self) -> None:
        sample_id = uuid4()
        pred_id = uuid4()
        preds = [
            BoundingBox(
                annotation_id=pred_id,
                x=0,
                y=0,
                width=10,
                height=10,
                label_id=uuid4(),
                confidence=0.9,
            )
        ]
        result = object_detection_metric.match_with_iou_matrix(
            sample_id=sample_id,
            predictions=preds,
            ground_truths=[],
            iou_matrix=np.empty((1, 0)),
            iou_threshold=0.5,
        )
        assert result.tp == 0
        assert result.fp == 1
        assert result.fn == 0
        assert result.unmatched_prediction_ids == [pred_id]

    def test_perfect_match(self) -> None:
        sample_id = uuid4()
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
        iou_matrix = np.array([[1.0]])
        result = object_detection_metric.match_with_iou_matrix(
            sample_id=sample_id,
            predictions=preds,
            ground_truths=gts,
            iou_matrix=iou_matrix,
            iou_threshold=0.5,
        )
        assert result.tp == 1
        assert result.fp == 0
        assert result.fn == 0
        assert len(result.matches) == 1
        assert result.matches[0].pred_id == pred_id
        assert result.matches[0].gt_id == gt_id
        assert result.matches[0].iou == pytest.approx(1.0)

    def test_no_match_below_threshold(self) -> None:
        sample_id = uuid4()
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
        gts = [BoundingBox(annotation_id=gt_id, x=5, y=5, width=10, height=10, label_id=label_id)]
        iou_matrix = np.array([[0.3]])
        result = object_detection_metric.match_with_iou_matrix(
            sample_id=sample_id,
            predictions=preds,
            ground_truths=gts,
            iou_matrix=iou_matrix,
            iou_threshold=0.5,
        )
        assert result.tp == 0
        assert result.fp == 1
        assert result.fn == 1
        assert result.unmatched_prediction_ids == [pred_id]
        assert result.unmatched_gt_ids == [gt_id]

    def test_match_at_exact_threshold(self) -> None:
        sample_id = uuid4()
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
        iou_matrix = np.array([[0.5]])
        result = object_detection_metric.match_with_iou_matrix(
            sample_id=sample_id,
            predictions=preds,
            ground_truths=gts,
            iou_matrix=iou_matrix,
            iou_threshold=0.5,
        )
        assert result.tp == 1
        assert result.fp == 0
        assert result.fn == 0

    def test_greedy_match_by_confidence(self) -> None:
        sample_id = uuid4()
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
            sample_id=sample_id,
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

    def test_multiple_preds_multiple_gts(self) -> None:
        sample_id = uuid4()
        pred_ids = [uuid4() for _ in range(3)]
        gt_ids = [uuid4() for _ in range(2)]
        label_id = uuid4()
        preds = [
            BoundingBox(
                annotation_id=pred_ids[0],
                x=0,
                y=0,
                width=10,
                height=10,
                label_id=label_id,
                confidence=0.9,
            ),
            BoundingBox(
                annotation_id=pred_ids[1],
                x=20,
                y=0,
                width=10,
                height=10,
                label_id=label_id,
                confidence=0.8,
            ),
            BoundingBox(
                annotation_id=pred_ids[2],
                x=40,
                y=0,
                width=10,
                height=10,
                label_id=label_id,
                confidence=0.7,
            ),
        ]
        gts = [
            BoundingBox(annotation_id=gt_ids[0], x=0, y=0, width=10, height=10, label_id=label_id),
            BoundingBox(annotation_id=gt_ids[1], x=20, y=0, width=10, height=10, label_id=label_id),
        ]
        iou_matrix = np.array(
            [
                [1.0, 0.0],
                [0.0, 1.0],
                [0.3, 0.3],
            ]
        )
        result = object_detection_metric.match_with_iou_matrix(
            sample_id=sample_id,
            predictions=preds,
            ground_truths=gts,
            iou_matrix=iou_matrix,
            iou_threshold=0.5,
        )
        assert result.tp == 2
        assert result.fp == 1
        assert result.fn == 0
        match_pred_ids = {m.pred_id for m in result.matches}
        match_gt_ids = {m.gt_id for m in result.matches}
        assert pred_ids[0] in match_pred_ids
        assert pred_ids[1] in match_pred_ids
        assert gt_ids[0] in match_gt_ids
        assert gt_ids[1] in match_gt_ids
        assert result.unmatched_prediction_ids == [pred_ids[2]]

    def test_pred_without_confidence_treated_as_zero(self) -> None:
        sample_id = uuid4()
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
            sample_id=sample_id,
            predictions=preds,
            ground_truths=gts,
            iou_matrix=iou_matrix,
            iou_threshold=0.5,
        )
        assert result.tp == 1
        assert result.matches[0].pred_id == pred_with_conf_id

    def test_all_preds_below_threshold(self) -> None:
        sample_id = uuid4()
        pred_ids = [uuid4() for _ in range(2)]
        gt_ids = [uuid4() for _ in range(2)]
        label_id = uuid4()
        preds = [
            BoundingBox(
                annotation_id=pred_ids[0],
                x=0,
                y=0,
                width=10,
                height=10,
                label_id=label_id,
                confidence=0.9,
            ),
            BoundingBox(
                annotation_id=pred_ids[1],
                x=20,
                y=0,
                width=10,
                height=10,
                label_id=label_id,
                confidence=0.8,
            ),
        ]
        gts = [
            BoundingBox(annotation_id=gt_ids[0], x=0, y=0, width=10, height=10, label_id=label_id),
            BoundingBox(annotation_id=gt_ids[1], x=20, y=0, width=10, height=10, label_id=label_id),
        ]
        iou_matrix = np.array(
            [
                [0.4, 0.1],
                [0.1, 0.3],
            ]
        )
        result = object_detection_metric.match_with_iou_matrix(
            sample_id=sample_id,
            predictions=preds,
            ground_truths=gts,
            iou_matrix=iou_matrix,
            iou_threshold=0.5,
        )
        assert result.tp == 0
        assert result.fp == 2
        assert result.fn == 2
        assert set(result.unmatched_prediction_ids) == set(pred_ids)
        assert set(result.unmatched_gt_ids) == set(gt_ids)


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
