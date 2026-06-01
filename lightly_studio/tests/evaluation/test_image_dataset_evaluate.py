from __future__ import annotations

from uuid import UUID

import pytest
from sqlmodel import Session

from lightly_studio.core.image.image_dataset import ImageDataset
from lightly_studio.evaluation.image_dataset_evaluate import (
    ClassificationEvaluationConfig,
    ObjectDetectionEvaluationConfig,
)
from lightly_studio.models.annotation.annotation_base import AnnotationType
from lightly_studio.models.collection import SampleType
from lightly_studio.models.evaluation_run import EvaluationTaskType
from lightly_studio.resolvers import (
    collection_resolver,
    evaluation_annotation_metric_resolver,
    evaluation_run_resolver,
    evaluation_sample_metric_resolver,
)
from tests.helpers_resolvers import create_annotation, create_annotation_label, create_image


def test_object_detection_evaluation(
    patch_collection: None,  # noqa: ARG001
) -> None:
    """Creates an evaluation run for object detection and persists sample metrics."""
    dataset = ImageDataset.create(name="test_dataset")
    label = create_annotation_label(
        session=dataset.session,
        root_collection_id=dataset.collection_id,
    )
    image = create_image(session=dataset.session, collection_id=dataset.collection_id)
    _create_gt_and_pred_collections(session=dataset.session, collection_id=dataset.collection_id)
    # This GT box overlaps the first prediction and should count as one TP.
    gt_tp = create_annotation(
        session=dataset.session,
        collection_id=dataset.collection_id,
        sample_id=image.sample_id,
        annotation_label_id=label.annotation_label_id,
        annotation_collection_name="gt",
    )
    # This GT box has no matching prediction and should count as one FN.
    gt_fn = create_annotation(
        session=dataset.session,
        collection_id=dataset.collection_id,
        sample_id=image.sample_id,
        annotation_label_id=label.annotation_label_id,
        annotation_data={"x": 100, "y": 100, "width": 20, "height": 20},
        annotation_collection_name="gt",
    )
    # This prediction overlaps the first GT box and should count as one TP.
    pred_tp = create_annotation(
        session=dataset.session,
        collection_id=dataset.collection_id,
        sample_id=image.sample_id,
        annotation_label_id=label.annotation_label_id,
        annotation_collection_name="pred",
    )
    # This prediction has no matching GT box and should count as one FP.
    pred_fp = create_annotation(
        session=dataset.session,
        collection_id=dataset.collection_id,
        sample_id=image.sample_id,
        annotation_label_id=label.annotation_label_id,
        annotation_data={"x": 200, "y": 200, "width": 20, "height": 20},
        annotation_collection_name="pred",
    )

    result = dataset.evaluate().object_detection(
        name="run-1",
        gt_annotation_source="gt",
        pred_annotation_source="pred",
        config=ObjectDetectionEvaluationConfig(iou_threshold=0.5),
    )
    assert result.sample_count == 1
    assert result.gt_annotation_count == 2
    assert result.pred_annotation_count == 2

    evaluation_runs = evaluation_run_resolver.get_all_by_dataset_id(
        session=dataset.session,
        dataset_id=dataset.dataset_id,
    )
    assert len(evaluation_runs) == 1
    assert evaluation_runs[0].name == "run-1"
    assert evaluation_runs[0].task_type == EvaluationTaskType.OBJECT_DETECTION
    assert evaluation_runs[0].config_json == {"iou_threshold": 0.5, "classwise": True}

    sample_metrics = evaluation_sample_metric_resolver.get_all_by_evaluation_run_id(
        session=dataset.session,
        evaluation_run_id=evaluation_runs[0].id,
    )
    assert {(metric.sample_id, metric.metric_name): metric.value for metric in sample_metrics} == {
        (image.sample_id, "tp"): 1.0,
        (image.sample_id, "fp"): 1.0,
        (image.sample_id, "fn"): 1.0,
    }

    annotation_metrics = evaluation_annotation_metric_resolver.get_all_by_evaluation_run_id(
        session=dataset.session,
        evaluation_run_id=evaluation_runs[0].id,
    )
    assert len(annotation_metrics) == 3
    annotation_metrics_by_type = {
        (m.pred_annotation_id, m.gt_annotation_id): m for m in annotation_metrics
    }
    # The TP metric has IoU value
    tp_metric = annotation_metrics_by_type[(pred_tp.sample_id, gt_tp.sample_id)]
    assert tp_metric.metric_name == "iou"
    assert tp_metric.value == pytest.approx(1.0)
    # The FP and FN metrics have no metric name or value
    fp_metric = annotation_metrics_by_type[(pred_fp.sample_id, None)]
    assert fp_metric.metric_name is None
    assert fp_metric.value is None
    fn_metric = annotation_metrics_by_type[(None, gt_fn.sample_id)]
    assert fn_metric.metric_name is None
    assert fn_metric.value is None


def test_object_detection_evaluation__raises_on_wrong_annotation_type(
    patch_collection: None,  # noqa: ARG001
) -> None:
    """Raises ValueError when a collection contains non-object-detection annotations."""
    dataset = ImageDataset.create(name="test_dataset")
    label = create_annotation_label(
        session=dataset.session, root_collection_id=dataset.collection_id
    )
    image = create_image(session=dataset.session, collection_id=dataset.collection_id)
    _create_gt_and_pred_collections(session=dataset.session, collection_id=dataset.collection_id)
    create_annotation(
        session=dataset.session,
        collection_id=dataset.collection_id,
        sample_id=image.sample_id,
        annotation_label_id=label.annotation_label_id,
        annotation_type=AnnotationType.CLASSIFICATION,
        annotation_collection_name="gt",
    )

    with pytest.raises(ValueError, match="object_detection"):
        dataset.evaluate().object_detection(
            name="run-1",
            gt_annotation_source="gt",
            pred_annotation_source="pred",
        )


def test_object_detection_evaluation__filters_to_samples_covered_by_both_collections(
    patch_collection: None,  # noqa: ARG001
) -> None:
    """Creates metrics only for samples covered by both GT and prediction collections."""
    dataset = ImageDataset.create(name="test_dataset")
    label = create_annotation_label(
        session=dataset.session,
        root_collection_id=dataset.collection_id,
    )
    image_covered_by_both = create_image(
        session=dataset.session,
        collection_id=dataset.collection_id,
        file_path_abs="/path/to/covered_by_both.png",
    )
    create_image(
        session=dataset.session,
        collection_id=dataset.collection_id,
        file_path_abs="/path/to/covered_only_by_gt.png",
    )
    create_image(
        session=dataset.session,
        collection_id=dataset.collection_id,
        file_path_abs="/path/to/uncovered.png",
    )
    _create_gt_and_pred_collections(session=dataset.session, collection_id=dataset.collection_id)
    create_annotation(
        session=dataset.session,
        collection_id=dataset.collection_id,
        sample_id=image_covered_by_both.sample_id,
        annotation_label_id=label.annotation_label_id,
        annotation_collection_name="gt",
    )
    create_annotation(
        session=dataset.session,
        collection_id=dataset.collection_id,
        sample_id=image_covered_by_both.sample_id,
        annotation_label_id=label.annotation_label_id,
        annotation_collection_name="pred",
    )

    result = dataset.evaluate().object_detection(
        name="run-1",
        gt_annotation_source="gt",
        pred_annotation_source="pred",
    )
    assert result.sample_count == 1
    assert result.gt_annotation_count == 1
    assert result.pred_annotation_count == 1

    evaluation_runs = evaluation_run_resolver.get_all_by_dataset_id(
        session=dataset.session,
        dataset_id=dataset.dataset_id,
    )
    assert len(evaluation_runs) == 1
    sample_metrics = evaluation_sample_metric_resolver.get_all_by_evaluation_run_id(
        session=dataset.session,
        evaluation_run_id=evaluation_runs[0].id,
    )
    assert len(sample_metrics) == 3
    assert {metric.sample_id for metric in sample_metrics} == {image_covered_by_both.sample_id}


@pytest.mark.parametrize(
    ("gt_label_name", "pred_label_name", "pred_confidence", "expected_disagreement"),
    [
        # Confidence values must be exactly representable in float32
        # (DB column is float32-precision).
        # agree, c=0.5 -> 1 - c = 0.5
        ("A", "A", 0.5, 0.5),
        # disagree, c=0.25 -> c = 0.25
        ("A", "B", 0.25, 0.25),
        # agree, c defaults to 1.0 -> 1 - c = 0.0
        ("A", "A", None, 0.0),
        # disagree, c defaults to 1.0 -> c = 1.0
        ("A", "B", None, 1.0),
    ],
)
def test_classification_evaluation(
    patch_collection: None,  # noqa: ARG001
    gt_label_name: str,
    pred_label_name: str,
    pred_confidence: float | None,
    expected_disagreement: float,
) -> None:
    """Persists per-sample disagreement metric for matching and mismatching labels."""
    dataset = ImageDataset.create(name="test_dataset")
    gt_label = create_annotation_label(
        session=dataset.session,
        root_collection_id=dataset.collection_id,
        label_name=gt_label_name,
    )
    pred_label = (
        gt_label
        if pred_label_name == gt_label_name
        else create_annotation_label(
            session=dataset.session,
            root_collection_id=dataset.collection_id,
            label_name=pred_label_name,
        )
    )
    image = create_image(session=dataset.session, collection_id=dataset.collection_id)
    _create_gt_and_pred_collections(session=dataset.session, collection_id=dataset.collection_id)
    create_annotation(
        session=dataset.session,
        collection_id=dataset.collection_id,
        sample_id=image.sample_id,
        annotation_label_id=gt_label.annotation_label_id,
        annotation_type=AnnotationType.CLASSIFICATION,
        annotation_collection_name="gt",
    )
    create_annotation(
        session=dataset.session,
        collection_id=dataset.collection_id,
        sample_id=image.sample_id,
        annotation_label_id=pred_label.annotation_label_id,
        annotation_type=AnnotationType.CLASSIFICATION,
        annotation_data=({"confidence": pred_confidence} if pred_confidence is not None else None),
        annotation_collection_name="pred",
    )

    result = dataset.evaluate().classification(
        name="run-1",
        gt_annotation_source="gt",
        pred_annotation_source="pred",
        config=ClassificationEvaluationConfig(),
    )
    assert result.sample_count == 1
    assert result.gt_annotation_count == 1
    assert result.pred_annotation_count == 1

    evaluation_runs = evaluation_run_resolver.get_all_by_dataset_id(
        session=dataset.session,
        dataset_id=dataset.dataset_id,
    )
    assert len(evaluation_runs) == 1
    assert evaluation_runs[0].name == "run-1"
    assert evaluation_runs[0].task_type == EvaluationTaskType.CLASSIFICATION
    assert evaluation_runs[0].config_json == {}

    sample_metrics = evaluation_sample_metric_resolver.get_all_by_evaluation_run_id(
        session=dataset.session,
        evaluation_run_id=evaluation_runs[0].id,
    )
    assert {(metric.sample_id, metric.metric_name): metric.value for metric in sample_metrics} == {
        (image.sample_id, "disagreement"): expected_disagreement,
    }


@pytest.mark.parametrize(
    ("collection_name", "kind"),
    [("gt", "ground truth"), ("pred", "prediction")],
)
def test_classification_evaluation__raises_on_multiple_annotations(
    patch_collection: None,  # noqa: ARG001
    collection_name: str,
    kind: str,
) -> None:
    """Raises ValueError when a sample has more than one annotation in one collection."""
    dataset = ImageDataset.create(name="test_dataset")
    label = create_annotation_label(
        session=dataset.session, root_collection_id=dataset.collection_id
    )
    image = create_image(session=dataset.session, collection_id=dataset.collection_id)
    _create_gt_and_pred_collections(session=dataset.session, collection_id=dataset.collection_id)
    # The other collection has exactly one annotation. Confidence only matters
    # for predictions, so only set it on the pred side.
    other_collection_name = "pred" if collection_name == "gt" else "gt"
    create_annotation(
        session=dataset.session,
        collection_id=dataset.collection_id,
        sample_id=image.sample_id,
        annotation_label_id=label.annotation_label_id,
        annotation_type=AnnotationType.CLASSIFICATION,
        annotation_data={"confidence": 0.5} if other_collection_name == "pred" else None,
        annotation_collection_name=other_collection_name,
    )
    # The target collection has two annotations on the same sample.
    for _ in range(2):
        create_annotation(
            session=dataset.session,
            collection_id=dataset.collection_id,
            sample_id=image.sample_id,
            annotation_label_id=label.annotation_label_id,
            annotation_type=AnnotationType.CLASSIFICATION,
            annotation_data={"confidence": 0.5} if collection_name == "pred" else None,
            annotation_collection_name=collection_name,
        )

    with pytest.raises(ValueError, match=f"exactly 1 {kind} annotation"):
        dataset.evaluate().classification(
            name="run-1",
            gt_annotation_source="gt",
            pred_annotation_source="pred",
        )


def test_classification_evaluation__raises_on_wrong_annotation_type(
    patch_collection: None,  # noqa: ARG001
) -> None:
    """Raises ValueError when a collection contains non-classification annotations."""
    dataset = ImageDataset.create(name="test_dataset")
    label = create_annotation_label(
        session=dataset.session, root_collection_id=dataset.collection_id
    )
    image = create_image(session=dataset.session, collection_id=dataset.collection_id)
    _create_gt_and_pred_collections(session=dataset.session, collection_id=dataset.collection_id)
    create_annotation(
        session=dataset.session,
        collection_id=dataset.collection_id,
        sample_id=image.sample_id,
        annotation_label_id=label.annotation_label_id,
        annotation_type=AnnotationType.OBJECT_DETECTION,
        annotation_collection_name="gt",
    )

    with pytest.raises(ValueError, match="classification"):
        dataset.evaluate().classification(
            name="run-1",
            gt_annotation_source="gt",
            pred_annotation_source="pred",
        )


def test_segmentation_evaluation(
    patch_collection: None,  # noqa: ARG001
) -> None:
    """Creates an evaluation run for semantic segmentation and returns sample counts."""
    dataset = ImageDataset.create(name="test_dataset")
    label = create_annotation_label(
        session=dataset.session,
        root_collection_id=dataset.collection_id,
    )
    image = create_image(session=dataset.session, collection_id=dataset.collection_id)
    _create_gt_and_pred_collections(session=dataset.session, collection_id=dataset.collection_id)
    create_annotation(
        session=dataset.session,
        collection_id=dataset.collection_id,
        sample_id=image.sample_id,
        annotation_label_id=label.annotation_label_id,
        annotation_type=AnnotationType.SEGMENTATION_MASK,
        annotation_collection_name="gt",
    )
    create_annotation(
        session=dataset.session,
        collection_id=dataset.collection_id,
        sample_id=image.sample_id,
        annotation_label_id=label.annotation_label_id,
        annotation_type=AnnotationType.SEGMENTATION_MASK,
        annotation_collection_name="pred",
    )

    result = dataset.evaluate().semantic_segmentation(
        name="seg-run-1",
        gt_annotation_source="gt",
        pred_annotation_source="pred",
    )
    assert result.sample_count == 1
    assert result.gt_annotation_count == 1
    assert result.pred_annotation_count == 1

    evaluation_runs = evaluation_run_resolver.get_all_by_dataset_id(
        session=dataset.session,
        dataset_id=dataset.dataset_id,
    )
    assert len(evaluation_runs) == 1
    assert evaluation_runs[0].name == "seg-run-1"
    assert evaluation_runs[0].task_type == EvaluationTaskType.SEMANTIC_SEGMENTATION


def test_segmentation_evaluation__raises_on_wrong_annotation_type(
    patch_collection: None,  # noqa: ARG001
) -> None:
    """Raises ValueError when a collection contains non-segmentation annotations."""
    dataset = ImageDataset.create(name="test_dataset")
    label = create_annotation_label(
        session=dataset.session, root_collection_id=dataset.collection_id
    )
    image = create_image(session=dataset.session, collection_id=dataset.collection_id)
    _create_gt_and_pred_collections(session=dataset.session, collection_id=dataset.collection_id)
    create_annotation(
        session=dataset.session,
        collection_id=dataset.collection_id,
        sample_id=image.sample_id,
        annotation_label_id=label.annotation_label_id,
        annotation_type=AnnotationType.OBJECT_DETECTION,
        annotation_collection_name="gt",
    )

    with pytest.raises(ValueError, match="segmentation_mask"):
        dataset.evaluate().semantic_segmentation(
            name="seg-run-1",
            gt_annotation_source="gt",
            pred_annotation_source="pred",
        )


def _create_gt_and_pred_collections(session: Session, collection_id: UUID) -> None:
    """Create child 'gt' and 'pred' annotation collections under the parent collection.

    Args:
        session: Database session used by resolver calls.
        collection_id: ID of the parent collection under which the child collections
            are created.
    """
    for name in ("gt", "pred"):
        collection_resolver.get_or_create_child_collection(
            session=session,
            collection_id=collection_id,
            sample_type=SampleType.ANNOTATION,
            name=name,
        )
