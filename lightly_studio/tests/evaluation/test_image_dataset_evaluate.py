from __future__ import annotations

from uuid import UUID, uuid4

import pytest
from sqlmodel import Session

from lightly_studio.core.image.image_dataset import ImageDataset
from lightly_studio.evaluation.image_dataset_evaluate import (
    ClassificationEvaluationConfig,
    ObjectDetectionEvaluationConfig,
)
from lightly_studio.models.annotation.annotation_base import AnnotationType
from lightly_studio.models.collection import SampleType
from lightly_studio.models.evaluation_confusion_matrix import (
    NO_GROUND_TRUTH_ROW_LABEL,
    NO_PREDICTION_COL_LABEL,
)
from lightly_studio.models.evaluation_run import EvaluationRunCreate, EvaluationTaskType
from lightly_studio.resolvers import (
    collection_resolver,
    evaluation_annotation_metric_resolver,
    evaluation_run_resolver,
    evaluation_sample_metric_resolver,
)
from tests.helpers_resolvers import (
    create_annotation,
    create_annotation_label,
    create_collection,
    create_image,
)


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
    gt_annotation = create_annotation(
        session=dataset.session,
        collection_id=dataset.collection_id,
        sample_id=image.sample_id,
        annotation_label_id=gt_label.annotation_label_id,
        annotation_type=AnnotationType.CLASSIFICATION,
        annotation_collection_name="gt",
    )
    pred_annotation = create_annotation(
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

    annotation_metrics = evaluation_annotation_metric_resolver.get_all_by_evaluation_run_id(
        session=dataset.session,
        evaluation_run_id=evaluation_runs[0].id,
    )
    assert len(annotation_metrics) == 1
    assert annotation_metrics[0].sample_id == image.sample_id
    assert annotation_metrics[0].gt_annotation_id == gt_annotation.sample_id
    assert annotation_metrics[0].pred_annotation_id == pred_annotation.sample_id
    assert annotation_metrics[0].metric_name == "disagreement"
    assert annotation_metrics[0].value == expected_disagreement


def test_classification_evaluation__persists_confusion_matrix_pairings(
    patch_collection: None,  # noqa: ARG001
) -> None:
    """Persists one GT/pred pairing per sample for confusion matrix aggregation."""
    dataset = ImageDataset.create(name="test_dataset")
    gt_label = create_annotation_label(
        session=dataset.session,
        root_collection_id=dataset.collection_id,
        label_name="cat",
    )
    pred_label = create_annotation_label(
        session=dataset.session,
        root_collection_id=dataset.collection_id,
        label_name="dog",
    )
    image = create_image(session=dataset.session, collection_id=dataset.collection_id)
    _create_gt_and_pred_collections(session=dataset.session, collection_id=dataset.collection_id)
    gt_annotation = create_annotation(
        session=dataset.session,
        collection_id=dataset.collection_id,
        sample_id=image.sample_id,
        annotation_label_id=gt_label.annotation_label_id,
        annotation_type=AnnotationType.CLASSIFICATION,
        annotation_collection_name="gt",
    )
    pred_annotation = create_annotation(
        session=dataset.session,
        collection_id=dataset.collection_id,
        sample_id=image.sample_id,
        annotation_label_id=pred_label.annotation_label_id,
        annotation_type=AnnotationType.CLASSIFICATION,
        annotation_data={"confidence": 0.75},
        annotation_collection_name="pred",
    )

    dataset.evaluate().classification(
        name="run-1",
        gt_annotation_source="gt",
        pred_annotation_source="pred",
    )

    evaluation_runs = evaluation_run_resolver.get_all_by_dataset_id(
        session=dataset.session,
        dataset_id=dataset.dataset_id,
    )
    annotation_metrics = evaluation_annotation_metric_resolver.get_all_by_evaluation_run_id(
        session=dataset.session,
        evaluation_run_id=evaluation_runs[0].id,
    )

    assert len(annotation_metrics) == 1
    assert annotation_metrics[0].gt_annotation_id == gt_annotation.sample_id
    assert annotation_metrics[0].pred_annotation_id == pred_annotation.sample_id
    assert annotation_metrics[0].metric_name == "disagreement"
    assert annotation_metrics[0].value == 0.75


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
    """Creates an evaluation run for semantic segmentation and persists per-image metrics."""
    dataset = ImageDataset.create(name="test_dataset")
    dog_label = create_annotation_label(
        session=dataset.session,
        root_collection_id=dataset.collection_id,
        label_name="dog",
    )
    image = create_image(
        session=dataset.session,
        collection_id=dataset.collection_id,
        width=4,
        height=3,
    )
    _create_gt_and_pred_collections(session=dataset.session, collection_id=dataset.collection_id)
    mask_data = {
        "x": 0,
        "y": 0,
        "width": 4,
        "height": 3,
        "segmentation_mask": [0, 4, 4, 4],
    }
    for collection_name in ("gt", "pred"):
        create_annotation(
            session=dataset.session,
            collection_id=dataset.collection_id,
            sample_id=image.sample_id,
            annotation_label_id=dog_label.annotation_label_id,
            annotation_type=AnnotationType.SEGMENTATION_MASK,
            annotation_data=mask_data,
            annotation_collection_name=collection_name,
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

    sample_metrics = evaluation_sample_metric_resolver.get_all_by_evaluation_run_id(
        session=dataset.session,
        evaluation_run_id=evaluation_runs[0].id,
    )
    assert len(sample_metrics) == 1
    metric = sample_metrics[0]
    assert metric.sample_id == image.sample_id
    assert metric.metric_name == "miou"
    assert metric.value == pytest.approx(1.0)


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


def test_list_runs(
    patch_collection: None,  # noqa: ARG001
) -> None:
    """Returns a view per run, with resolved source names and the run configuration."""
    dataset = ImageDataset.create(name="test_dataset")
    label = create_annotation_label(
        session=dataset.session,
        root_collection_id=dataset.collection_id,
    )
    image = create_image(session=dataset.session, collection_id=dataset.collection_id)
    _create_gt_and_pred_collections(session=dataset.session, collection_id=dataset.collection_id)
    for source_name in ("gt", "pred"):
        create_annotation(
            session=dataset.session,
            collection_id=dataset.collection_id,
            sample_id=image.sample_id,
            annotation_label_id=label.annotation_label_id,
            annotation_collection_name=source_name,
        )
    for run_name in ("run-a", "run-b"):
        dataset.evaluate().object_detection(
            name=run_name,
            gt_annotation_source="gt",
            pred_annotation_source="pred",
        )

    views = dataset.evaluate().list_runs()

    assert len(views) == 2
    assert {view.name for view in views} == {"run-a", "run-b"}
    view = next(view for view in views if view.name == "run-a")
    assert view.gt_annotation_source == "gt"
    assert view.pred_annotation_source == "pred"
    assert set(view.evaluation_run_configuration) == {"iou_threshold", "classwise"}


def test_list_runs__no_runs_returns_empty(
    patch_collection: None,  # noqa: ARG001
) -> None:
    """Returns an empty list when the dataset has no evaluation runs."""
    dataset = ImageDataset.create(name="test_dataset")

    assert dataset.evaluate().list_runs() == []


def test_confusion_matrix(
    patch_collection: None,  # noqa: ARG001
) -> None:
    """Returns the confusion matrix for a run from its persisted annotation pairings."""
    dataset = ImageDataset.create(name="test_dataset")
    gt_label = create_annotation_label(
        session=dataset.session,
        root_collection_id=dataset.collection_id,
        label_name="cat",
    )
    pred_label = create_annotation_label(
        session=dataset.session,
        root_collection_id=dataset.collection_id,
        label_name="dog",
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
        annotation_collection_name="pred",
    )
    dataset.evaluate().classification(
        name="run-1",
        gt_annotation_source="gt",
        pred_annotation_source="pred",
    )
    run_id = dataset.evaluate().list_runs()[0].id

    matrix = dataset.evaluate().confusion_matrix(run_id=run_id)

    assert matrix.row_labels == ["cat", "dog", NO_GROUND_TRUTH_ROW_LABEL]
    assert matrix.col_labels == ["cat", "dog", NO_PREDICTION_COL_LABEL]
    assert matrix.counts == [[0, 1, 0], [0, 0, 0], [0, 0, 0]]


def test_confusion_matrix__run_not_found_raises(
    patch_collection: None,  # noqa: ARG001
) -> None:
    """Raises ValueError when the run does not exist."""
    dataset = ImageDataset.create(name="test_dataset")

    with pytest.raises(ValueError, match="not found"):
        dataset.evaluate().confusion_matrix(run_id=uuid4())


def test_confusion_matrix__unsupported_task_type_raises(
    patch_collection: None,  # noqa: ARG001
) -> None:
    """Raises NotImplementedError for a task type without a confusion matrix."""
    dataset = ImageDataset.create(name="test_dataset")
    gt_collection = create_collection(
        session=dataset.session,
        parent_collection_id=dataset.collection_id,
        sample_type=SampleType.ANNOTATION,
    )
    pred_collection = create_collection(
        session=dataset.session,
        parent_collection_id=dataset.collection_id,
        sample_type=SampleType.ANNOTATION,
    )
    run = evaluation_run_resolver.create(
        session=dataset.session,
        evaluation_run_input=EvaluationRunCreate(
            name="seg-run",
            gt_annotation_collection_id=gt_collection.collection_id,
            pred_annotation_collection_id=pred_collection.collection_id,
            dataset_id=dataset.dataset_id,
            task_type=EvaluationTaskType.SEMANTIC_SEGMENTATION,
        ),
    )

    with pytest.raises(NotImplementedError, match="semantic_segmentation"):
        dataset.evaluate().confusion_matrix(run_id=run.id)


def test_confusion_matrix__run_from_another_dataset_raises(
    patch_collection: None,  # noqa: ARG001
) -> None:
    """Rejects a run that belongs to a different dataset."""
    other_dataset = ImageDataset.create(name="other_dataset")
    gt_collection = create_collection(
        session=other_dataset.session,
        parent_collection_id=other_dataset.collection_id,
        sample_type=SampleType.ANNOTATION,
    )
    pred_collection = create_collection(
        session=other_dataset.session,
        parent_collection_id=other_dataset.collection_id,
        sample_type=SampleType.ANNOTATION,
    )
    run = evaluation_run_resolver.create(
        session=other_dataset.session,
        evaluation_run_input=EvaluationRunCreate(
            name="run-1",
            gt_annotation_collection_id=gt_collection.collection_id,
            pred_annotation_collection_id=pred_collection.collection_id,
            dataset_id=other_dataset.dataset_id,
            task_type=EvaluationTaskType.OBJECT_DETECTION,
        ),
    )
    dataset = ImageDataset.create(name="test_dataset")

    with pytest.raises(ValueError, match="not found in this dataset"):
        dataset.evaluate().confusion_matrix(run_id=run.id)


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
