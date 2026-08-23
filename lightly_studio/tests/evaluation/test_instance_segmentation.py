"""Tests for instance segmentation evaluation primitives."""

from __future__ import annotations

from uuid import UUID, uuid4

import numpy as np
import pytest
from numpy.typing import NDArray
from sqlmodel import Session

from lightly_studio.evaluation import instance_segmentation_metric
from lightly_studio.evaluation.instance_segmentation_metric import (
    InstanceMask,
    compute_mask_iou_matrix,
)
from lightly_studio.models.annotation.annotation_base import AnnotationType
from tests.helpers_resolvers import (
    create_annotation,
    create_annotation_label,
    create_collection,
    create_image,
)


def _mask(rows: slice, cols: slice, size: int = 10) -> NDArray[np.bool_]:
    mask = np.zeros((size, size), dtype=np.bool_)
    mask[rows, cols] = True
    return mask


def _instance(
    mask: NDArray[np.bool_],
    label_id: UUID,
    confidence: float | None = None,
    annotation_id: UUID | None = None,
) -> InstanceMask:
    return InstanceMask(
        annotation_id=annotation_id or uuid4(),
        mask=mask,
        label_id=label_id,
        confidence=confidence,
    )


def test_compute_mask_iou_matrix__known_values() -> None:
    pred = _mask(slice(0, 4), slice(0, 4))  # 16 px
    identical = _mask(slice(0, 4), slice(0, 4))  # IoU 1.0
    half = _mask(slice(0, 4), slice(0, 2))  # 8 px subset -> 8/16 = 0.5
    disjoint = _mask(slice(5, 9), slice(5, 9))  # no overlap -> 0.0
    matrix = compute_mask_iou_matrix([pred], [identical, half, disjoint])
    assert matrix.shape == (1, 3)
    np.testing.assert_allclose(matrix[0], [1.0, 0.5, 0.0])


def test_compute_mask_iou_matrix__empty_masks_are_zero() -> None:
    empty = np.zeros((10, 10), dtype=np.bool_)
    matrix = compute_mask_iou_matrix([empty], [empty])
    assert matrix.tolist() == [[0.0]]


def test_match_image__no_preds_no_gts() -> None:
    result = instance_segmentation_metric.match_image(
        predictions=[], ground_truths=[], iou_threshold=0.5, classwise=False
    )
    assert (result.tp, result.fp, result.fn) == (0, 0, 0)


def test_match_image__single_class_perfect_match() -> None:
    label_id = uuid4()
    pred_id, gt_id = uuid4(), uuid4()
    block = _mask(slice(0, 4), slice(0, 4))
    preds = [_instance(block, label_id, confidence=0.9, annotation_id=pred_id)]
    gts = [_instance(block, label_id, annotation_id=gt_id)]
    result = instance_segmentation_metric.match_image(
        predictions=preds, ground_truths=gts, iou_threshold=0.5, classwise=False
    )
    assert (result.tp, result.fp, result.fn) == (1, 0, 0)
    assert result.matches[0].pred_id == pred_id
    assert result.matches[0].gt_id == gt_id
    assert result.matches[0].iou == 1.0


def test_match_image__below_threshold_is_fp_and_fn() -> None:
    label_id = uuid4()
    pred = _instance(_mask(slice(0, 4), slice(0, 1)), label_id, confidence=0.9)  # 4 px
    gt = _instance(_mask(slice(0, 4), slice(0, 4)), label_id)  # 16 px, IoU 4/16 = 0.25
    result = instance_segmentation_metric.match_image(
        predictions=[pred], ground_truths=[gt], iou_threshold=0.5, classwise=False
    )
    assert (result.tp, result.fp, result.fn) == (0, 1, 1)


def test_match_image__classwise_same_class_as_non_classwise() -> None:
    label_id = uuid4()
    block = _mask(slice(0, 4), slice(0, 4))
    preds = [_instance(block, label_id, confidence=0.9)]
    gts = [_instance(block, label_id)]
    classwise = instance_segmentation_metric.match_image(
        predictions=preds, ground_truths=gts, iou_threshold=0.5, classwise=True
    )
    non_classwise = instance_segmentation_metric.match_image(
        predictions=preds, ground_truths=gts, iou_threshold=0.5, classwise=False
    )
    assert (classwise.tp, classwise.fp, classwise.fn) == (
        non_classwise.tp,
        non_classwise.fp,
        non_classwise.fn,
    )


def test_match_image__classwise_prevents_cross_class_match() -> None:
    block = _mask(slice(0, 4), slice(0, 4))
    pred_id, gt_id = uuid4(), uuid4()
    preds = [_instance(block, uuid4(), confidence=0.9, annotation_id=pred_id)]
    gts = [_instance(block, uuid4(), annotation_id=gt_id)]
    result = instance_segmentation_metric.match_image(
        predictions=preds, ground_truths=gts, iou_threshold=0.5, classwise=True
    )
    assert (result.tp, result.fp, result.fn) == (0, 1, 1)
    assert result.unmatched_prediction_ids == [pred_id]
    assert result.unmatched_gt_ids == [gt_id]


def test_match_image__non_classwise_allows_cross_class_match() -> None:
    block = _mask(slice(0, 4), slice(0, 4))
    preds = [_instance(block, uuid4(), confidence=0.9)]
    gts = [_instance(block, uuid4())]
    result = instance_segmentation_metric.match_image(
        predictions=preds, ground_truths=gts, iou_threshold=0.5, classwise=False
    )
    assert (result.tp, result.fp, result.fn) == (1, 0, 0)


def test_match_image__classwise_multiple_classes() -> None:
    label_a, label_b = uuid4(), uuid4()
    pred_a, pred_b, gt_a, gt_b = uuid4(), uuid4(), uuid4(), uuid4()
    mask_a = _mask(slice(0, 4), slice(0, 4))
    mask_b = _mask(slice(5, 9), slice(5, 9))
    preds = [
        _instance(mask_a, label_a, confidence=0.9, annotation_id=pred_a),
        _instance(mask_b, label_b, confidence=0.8, annotation_id=pred_b),
    ]
    gts = [
        _instance(mask_a, label_a, annotation_id=gt_a),
        _instance(mask_b, label_b, annotation_id=gt_b),
    ]
    result = instance_segmentation_metric.match_image(
        predictions=preds, ground_truths=gts, iou_threshold=0.5, classwise=True
    )
    assert (result.tp, result.fp, result.fn) == (2, 0, 0)
    match_ids = {m.pred_id: m.gt_id for m in result.matches}
    assert match_ids[pred_a] == gt_a
    assert match_ids[pred_b] == gt_b


def test_match_image__one_gt_matches_highest_confidence_pred() -> None:
    label_id = uuid4()
    gt_id, high_id, low_id = uuid4(), uuid4(), uuid4()
    block = _mask(slice(0, 4), slice(0, 4))
    preds = [
        _instance(block, label_id, confidence=0.6, annotation_id=low_id),
        _instance(block, label_id, confidence=0.95, annotation_id=high_id),
    ]
    gts = [_instance(block, label_id, annotation_id=gt_id)]
    result = instance_segmentation_metric.match_image(
        predictions=preds, ground_truths=gts, iou_threshold=0.5, classwise=False
    )
    assert (result.tp, result.fp, result.fn) == (1, 1, 0)
    assert result.matches[0].pred_id == high_id
    assert result.unmatched_prediction_ids == [low_id]


def test_match_image__empty_preds_all_fn() -> None:
    label_id = uuid4()
    gts = [_instance(_mask(slice(0, 4), slice(0, 4)), label_id)]
    result = instance_segmentation_metric.match_image(
        predictions=[], ground_truths=gts, iou_threshold=0.5, classwise=False
    )
    assert (result.tp, result.fp, result.fn) == (0, 0, 1)


def test_match_image__empty_gts_all_fp() -> None:
    label_id = uuid4()
    preds = [_instance(_mask(slice(0, 4), slice(0, 4)), label_id, confidence=0.9)]
    result = instance_segmentation_metric.match_image(
        predictions=preds, ground_truths=[], iou_threshold=0.5, classwise=False
    )
    assert (result.tp, result.fp, result.fn) == (0, 1, 0)


def test_to_instance_masks__decodes_fields(db_session: Session) -> None:
    collection = create_collection(session=db_session)
    label = create_annotation_label(session=db_session, root_collection_id=collection.collection_id)
    image = create_image(
        session=db_session, collection_id=collection.collection_id, width=2, height=2
    )
    annotation = create_annotation(
        session=db_session,
        collection_id=collection.collection_id,
        sample_id=image.sample_id,
        annotation_label_id=label.annotation_label_id,
        annotation_type=AnnotationType.SEGMENTATION_MASK,
        annotation_data={
            "x": 0,
            "y": 0,
            "width": 2,
            "height": 2,
            "segmentation_mask": [0, 4],
            "confidence": 0.8,
        },
    )

    masks = instance_segmentation_metric._to_instance_masks(annotations=[annotation], image=image)

    assert len(masks) == 1
    assert masks[0].annotation_id == annotation.sample_id
    assert masks[0].label_id == label.annotation_label_id
    assert masks[0].confidence == pytest.approx(0.8)
    assert masks[0].mask.shape == (2, 2)
    assert masks[0].mask.all()


def test_to_instance_masks__skips_missing_segmentation_details(db_session: Session) -> None:
    collection = create_collection(session=db_session)
    label = create_annotation_label(session=db_session, root_collection_id=collection.collection_id)
    image = create_image(session=db_session, collection_id=collection.collection_id)
    annotation = create_annotation(
        session=db_session,
        collection_id=collection.collection_id,
        sample_id=image.sample_id,
        annotation_label_id=label.annotation_label_id,
        annotation_type=AnnotationType.OBJECT_DETECTION,
    )

    masks = instance_segmentation_metric._to_instance_masks(annotations=[annotation], image=image)

    assert masks == []
