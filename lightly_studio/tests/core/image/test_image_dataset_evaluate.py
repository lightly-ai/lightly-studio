from __future__ import annotations

from lightly_studio.core.image.image_dataset import ImageDataset
from lightly_studio.evaluation.image_dataset_evaluate import ObjectDetectionEvaluationConfig
from lightly_studio.models.collection import SampleType
from lightly_studio.models.evaluation_run import EvaluationTaskType
from lightly_studio.models.evaluation_sample_metric import EvaluationSampleMetricTable
from lightly_studio.resolvers import (
    collection_resolver,
    evaluation_run_resolver,
    evaluation_sample_metric_resolver,
)
from tests.helpers_resolvers import (
    create_annotation,
    create_annotation_label,
    create_image,
)


def test_object_detection_evaluation(
    patch_collection: None,  # noqa: ARG001
) -> None:
    """Creates an evaluation run and persists per-sample TP/FP/FN metrics."""
    dataset = ImageDataset.create(name="test_dataset")
    sample = create_image(
        session=dataset.session,
        collection_id=dataset.collection_id,
        file_path_abs="/tmp/sample_1.png",
    )
    label = create_annotation_label(
        session=dataset.session,
        root_collection_id=dataset.collection_id,
        label_name="cat",
    )
    gt_collection_id = collection_resolver.get_or_create_child_collection(
        session=dataset.session,
        collection_id=dataset.collection_id,
        sample_type=SampleType.ANNOTATION,
        name="gt",
    )
    pred_collection_id = collection_resolver.get_or_create_child_collection(
        session=dataset.session,
        collection_id=dataset.collection_id,
        sample_type=SampleType.ANNOTATION,
        name="pred",
    )
    create_annotation(
        session=dataset.session,
        collection_id=dataset.collection_id,
        sample_id=sample.sample_id,
        annotation_label_id=label.annotation_label_id,
        annotation_collection_name="gt",
        annotation_data={"x": 10, "y": 10, "width": 10, "height": 10},
    )
    create_annotation(
        session=dataset.session,
        collection_id=dataset.collection_id,
        sample_id=sample.sample_id,
        annotation_label_id=label.annotation_label_id,
        annotation_collection_name="pred",
        annotation_data={"x": 10, "y": 10, "width": 10, "height": 10, "confidence": 0.9},
    )
    create_annotation(
        session=dataset.session,
        collection_id=dataset.collection_id,
        sample_id=sample.sample_id,
        annotation_label_id=label.annotation_label_id,
        annotation_collection_name="pred",
        annotation_data={"x": 100, "y": 100, "width": 10, "height": 10, "confidence": 0.8},
    )

    metrics = dataset.evaluate().object_detection(
        name="run-1",
        gt_collection_id=gt_collection_id,
        pred_collection_id=pred_collection_id,
        config=ObjectDetectionEvaluationConfig(iou_threshold=0.5),
    )

    assert metrics == {}

    evaluation_runs = evaluation_run_resolver.get_all_by_dataset_id(
        session=dataset.session,
        dataset_id=dataset.dataset_id,
    )
    assert len(evaluation_runs) == 1
    assert evaluation_runs[0].name == "run-1"
    assert evaluation_runs[0].task_type == EvaluationTaskType.OBJECT_DETECTION
    assert evaluation_runs[0].config_json == {"iou_threshold": 0.5}

    sample_metrics = evaluation_sample_metric_resolver.get_all_by_evaluation_run_id(
        session=dataset.session,
        evaluation_run_id=evaluation_runs[0].id,
    )
    assert len(sample_metrics) == 3
    assert {metric.metric_name for metric in sample_metrics} == {"tp", "fp", "fn"}

    metrics_by_name = {
        metric.metric_name: metric
        for metric in sample_metrics
        if metric.sample_id == sample.sample_id
    }
    assert metrics_by_name["tp"].value == 1
    assert metrics_by_name["fp"].value == 1
    assert metrics_by_name["fn"].value == 0
    assert all(isinstance(metric, EvaluationSampleMetricTable) for metric in sample_metrics)
