"""Tests for semantic segmentation evaluation metric primitives."""

from __future__ import annotations

from uuid import uuid4

import numpy as np
import pytest
from sqlmodel import Session

from lightly_studio.evaluation import semantic_segmentation_metric
from lightly_studio.models.annotation.annotation_base import AnnotationType
from tests.helpers_resolvers import (
    create_annotation,
    create_annotation_label,
    create_collection,
    create_image,
)


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


def test_class_masks_from_annotations__single_annotation(db_session: Session) -> None:
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
        annotation_data={"x": 0, "y": 0, "width": 2, "height": 2, "segmentation_mask": [0, 4]},
    )

    masks = semantic_segmentation_metric._class_masks_from_annotations(
        annotations=[annotation],
        image=image,
    )

    assert list(masks.keys()) == [label.annotation_label_id]
    assert masks[label.annotation_label_id].shape == (2, 2)
    assert masks[label.annotation_label_id].all()


def test_class_masks_from_annotations__accumulates_same_label(db_session: Session) -> None:
    collection = create_collection(session=db_session)
    label = create_annotation_label(session=db_session, root_collection_id=collection.collection_id)
    image = create_image(
        session=db_session, collection_id=collection.collection_id, width=2, height=2
    )
    ann1 = create_annotation(
        session=db_session,
        collection_id=collection.collection_id,
        sample_id=image.sample_id,
        annotation_label_id=label.annotation_label_id,
        annotation_type=AnnotationType.SEGMENTATION_MASK,
        annotation_data={"x": 0, "y": 0, "width": 2, "height": 1, "segmentation_mask": [0, 2, 2]},
    )
    ann2 = create_annotation(
        session=db_session,
        collection_id=collection.collection_id,
        sample_id=image.sample_id,
        annotation_label_id=label.annotation_label_id,
        annotation_type=AnnotationType.SEGMENTATION_MASK,
        annotation_data={"x": 0, "y": 1, "width": 2, "height": 1, "segmentation_mask": [2, 2]},
    )

    masks = semantic_segmentation_metric._class_masks_from_annotations(
        annotations=[ann1, ann2],
        image=image,
    )

    assert masks[label.annotation_label_id].shape == (2, 2)
    assert masks[label.annotation_label_id].all()


def test_class_masks_from_annotations__skips_missing_segmentation_details(
    db_session: Session,
) -> None:
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

    masks = semantic_segmentation_metric._class_masks_from_annotations(
        annotations=[annotation],
        image=image,
    )

    assert masks == {}


def test_sample_metric_record() -> None:
    evaluation_run_id = uuid4()
    sample_id = uuid4()

    record = semantic_segmentation_metric._sample_metric_record(
        evaluation_run_id=evaluation_run_id,
        sample_id=sample_id,
        class_ious={uuid4(): 0.8},
    )

    assert record.evaluation_run_id == evaluation_run_id
    assert record.sample_id == sample_id
    assert record.metric_name == "miou"
    assert record.value == pytest.approx(0.8)


def test_sample_metric_record__multiple_classes() -> None:
    record = semantic_segmentation_metric._sample_metric_record(
        evaluation_run_id=uuid4(),
        sample_id=uuid4(),
        class_ious={uuid4(): 0.6, uuid4(): 0.4},
    )

    assert record.value == pytest.approx(0.5)
