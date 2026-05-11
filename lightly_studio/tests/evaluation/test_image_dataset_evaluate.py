from __future__ import annotations

import pytest

from lightly_studio.core.image.image_dataset import ImageDataset
from lightly_studio.evaluation.image_dataset_evaluate import ObjectDetectionEvaluationConfig
from lightly_studio.models.annotation.annotation_base import AnnotationType
from lightly_studio.models.collection import SampleType
from lightly_studio.models.evaluation_run import EvaluationTaskType
from lightly_studio.resolvers import (
    collection_resolver,
    evaluation_run_resolver,
    evaluation_sample_metric_resolver,
)
from tests.helpers_resolvers import create_annotation, create_annotation_label, create_image


def test_object_detection_evaluation(
    patch_collection: None,  # noqa: ARG001
) -> None:
    """Creates an evaluation run for object detection and no sample metrics yet."""
    dataset = ImageDataset.create(name="test_dataset")
    collection_resolver.get_or_create_child_collection(
        session=dataset.session,
        collection_id=dataset.collection_id,
        sample_type=SampleType.ANNOTATION,
        name="gt",
    )
    collection_resolver.get_or_create_child_collection(
        session=dataset.session,
        collection_id=dataset.collection_id,
        sample_type=SampleType.ANNOTATION,
        name="pred",
    )

    dataset.evaluate().object_detection(
        name="run-1",
        gt_collection_name="gt",
        pred_collection_name="pred",
        config=ObjectDetectionEvaluationConfig(iou_threshold=0.5),
    )

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
    assert sample_metrics == []


def test_object_detection_evaluation__raises_on_wrong_annotation_type(
    patch_collection: None,  # noqa: ARG001
) -> None:
    """Raises ValueError when a collection contains non-object-detection annotations."""
    dataset = ImageDataset.create(name="test_dataset")
    label = create_annotation_label(
        session=dataset.session, root_collection_id=dataset.collection_id
    )
    image = create_image(session=dataset.session, collection_id=dataset.collection_id)
    collection_resolver.get_or_create_child_collection(
        session=dataset.session,
        collection_id=dataset.collection_id,
        sample_type=SampleType.ANNOTATION,
        name="gt",
    )
    collection_resolver.get_or_create_child_collection(
        session=dataset.session,
        collection_id=dataset.collection_id,
        sample_type=SampleType.ANNOTATION,
        name="pred",
    )
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
            gt_collection_name="gt",
            pred_collection_name="pred",
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
    collection_resolver.get_or_create_child_collection(
        session=dataset.session,
        collection_id=dataset.collection_id,
        sample_type=SampleType.ANNOTATION,
        name="gt",
    )
    collection_resolver.get_or_create_child_collection(
        session=dataset.session,
        collection_id=dataset.collection_id,
        sample_type=SampleType.ANNOTATION,
        name="pred",
    )
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

    dataset.evaluate().object_detection(
        name="run-1",
        gt_collection_name="gt",
        pred_collection_name="pred",
    )

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
