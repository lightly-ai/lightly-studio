from __future__ import annotations

from lightly_studio.core.image.image_dataset import ImageDataset
from lightly_studio.core.image.image_dataset_evaluate import ObjectDetectionEvaluationConfig
from lightly_studio.models.collection import SampleType
from lightly_studio.models.evaluation_run import EvaluationTaskType
from lightly_studio.resolvers import (
    collection_resolver,
    evaluation_run_resolver,
    evaluation_sample_metric_resolver,
)


def test_object_detection_evaluation(
    patch_collection: None,  # noqa: ARG001
) -> None:
    """Creates an evaluation run for object detection and no sample metrics yet."""
    dataset = ImageDataset.create(name="test_dataset")
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
    assert sample_metrics == []
