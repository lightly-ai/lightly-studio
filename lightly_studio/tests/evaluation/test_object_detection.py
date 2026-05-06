"""Tests for object detection evaluation primitives."""

from __future__ import annotations

from uuid import UUID, uuid4

from lightly_studio.evaluation import object_detection
from lightly_studio.evaluation.object_detection import (
    BoundingBox,
    DetectionMatch,
    ImageMatchingResult,
)

_SAMPLE_ID = UUID("00000000-0000-0000-0000-000000000001")
_LABEL_A = UUID("00000000-0000-0000-0000-000000000101")
_LABEL_B = UUID("00000000-0000-0000-0000-000000000102")
_IOU_THRESHOLD = 0.5


def _box(
    x: float = 0.0,
    y: float = 0.0,
    w: float = 10.0,
    h: float = 10.0,
    label: UUID = _LABEL_A,
    confidence: float | None = None,
    uuid: UUID | None = None,
) -> BoundingBox:
    return BoundingBox(
        uuid=uuid or uuid4(),
        x=x,
        y=y,
        width=w,
        height=h,
        label=label,
        confidence=confidence,
    )


def _run(
    ground_truths: list[BoundingBox],
    predictions: list[BoundingBox],
    iou_threshold: float = _IOU_THRESHOLD,
) -> ImageMatchingResult:
    return object_detection.match_with_iou_matrix(
        sample_id=_SAMPLE_ID,
        predictions=predictions,
        ground_truths=ground_truths,
        iou_matrix=object_detection.compute_iou_matrix(
            pred_corners=object_detection.to_corner_array(predictions),
            gt_corners=object_detection.to_corner_array(ground_truths),
        ),
        iou_threshold=iou_threshold,
    )


class TestMatchWithIouMatrix:
    def test_empty_both(self) -> None:
        r = _run([], [])
        assert r.tp == 0 and r.fp == 0 and r.fn == 0

    def test_empty_predictions(self) -> None:
        r = _run([_box(), _box(x=20.0)], [])
        assert r.tp == 0 and r.fp == 0 and r.fn == 2

    def test_empty_ground_truths(self) -> None:
        r = _run([], [_box(confidence=0.9), _box(x=20.0, confidence=0.8)])
        assert r.tp == 0 and r.fp == 2 and r.fn == 0

    def test_perfect_match(self) -> None:
        r = _run([_box()], [_box(confidence=0.9)])
        assert r.tp == 1 and r.fp == 0 and r.fn == 0

    def test_iou_below_threshold(self) -> None:
        # Shift prediction far enough that IoU < 0.5
        r = _run([_box()], [_box(x=8.0, confidence=0.9)])
        assert r.tp == 0 and r.fp == 1 and r.fn == 1

    def test_each_gt_matched_at_most_once(self) -> None:
        r = _run([_box()], [_box(confidence=0.9), _box(confidence=0.6)])
        assert r.tp == 1 and r.fp == 1 and r.fn == 0

    def test_partial_match(self) -> None:
        gts = [_box(), _box(x=50.0), _box(x=100.0, label=_LABEL_B)]
        preds = [
            _box(confidence=0.9),
            _box(x=100.0, label=_LABEL_B, confidence=0.8),
            _box(x=200.0, confidence=0.7),
        ]
        r = _run(gts, preds)
        assert r.tp == 2 and r.fp == 1 and r.fn == 1

    def test_high_confidence_matched_first(self) -> None:
        r = _run(
            [_box(x=0.0)],
            [_box(x=1.0, confidence=0.95), _box(x=2.0, confidence=0.6)],
            iou_threshold=0.3,
        )
        assert r.tp == 1 and r.fp == 1 and r.fn == 0

    def test_match_contains_correct_uuids_and_iou(self) -> None:
        pred_uuid = uuid4()
        gt_uuid = uuid4()
        r = _run([_box(uuid=gt_uuid)], [_box(uuid=pred_uuid, confidence=0.9)])
        assert r.matches == [DetectionMatch(pred_uuid=pred_uuid, gt_uuid=gt_uuid, iou=1.0)]

    def test_unmatched_lists_contain_correct_uuids(self) -> None:
        fp_uuid = uuid4()
        fn_uuid = uuid4()
        r = _run(
            [_box(x=100.0, uuid=fn_uuid)],
            [_box(x=0.0, uuid=fp_uuid, confidence=0.9)],
        )
        assert r.unmatched_prediction_uuids == [fp_uuid]
        assert r.unmatched_gt_uuids == [fn_uuid]

    def test_high_confidence_pred_gets_match(self) -> None:
        gt_uuid = uuid4()
        pred_high_uuid = uuid4()
        pred_low_uuid = uuid4()
        r = _run(
            [_box(x=0.0, uuid=gt_uuid)],
            [
                _box(x=0.0, uuid=pred_low_uuid, confidence=0.6),
                _box(x=0.0, uuid=pred_high_uuid, confidence=0.9),
            ],
        )
        assert r.matches == [DetectionMatch(pred_uuid=pred_high_uuid, gt_uuid=gt_uuid, iou=1.0)]
        assert r.unmatched_prediction_uuids == [pred_low_uuid]

    def test_properties_consistent_with_lists(self) -> None:
        r = _run([_box(), _box(x=50.0)], [_box(confidence=0.9)])
        assert r.tp == len(r.matches)
        assert r.fp == len(r.unmatched_prediction_uuids)
        assert r.fn == len(r.unmatched_gt_uuids)
