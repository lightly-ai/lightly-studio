"""Unit tests for the run_evaluation service (orchestration + validation)."""

from __future__ import annotations

import pytest
from sqlmodel import Session

from lightly_studio.evaluation.image_dataset_evaluate import (
    ClassificationEvaluationConfig,
    ObjectDetectionEvaluationConfig,
)
from lightly_studio.models.annotation.annotation_base import AnnotationType
from lightly_studio.models.collection import CollectionTable, SampleType
from lightly_studio.models.evaluation_run import EvaluationTaskType
from lightly_studio.resolvers import evaluation_run_resolver
from lightly_studio.resolvers.image_filter import ImageFilter
from lightly_studio.services import evaluation_service
from tests.helpers_resolvers import (
    create_annotation,
    create_annotation_label,
    create_collection,
    create_image,
)


def _create_dataset_with_annotations(
    db_session: Session,
    annotation_type: AnnotationType = AnnotationType.OBJECT_DETECTION,
    image_widths: tuple[int, ...] = (1920,),
) -> CollectionTable:
    """Create a root image collection with 'gt'/'pred' annotation sources."""
    root = create_collection(session=db_session)
    label = create_annotation_label(session=db_session, root_collection_id=root.collection_id)
    for source_name in ("gt", "pred"):
        create_collection(
            session=db_session,
            collection_name=source_name,
            parent_collection_id=root.collection_id,
            sample_type=SampleType.ANNOTATION,
        )
    for index, width in enumerate(image_widths):
        image = create_image(
            session=db_session,
            collection_id=root.collection_id,
            file_path_abs=f"/path/to/sample_{index}.png",
            width=width,
        )
        for source_name in ("gt", "pred"):
            create_annotation(
                session=db_session,
                collection_id=root.collection_id,
                sample_id=image.sample_id,
                annotation_label_id=label.annotation_label_id,
                annotation_type=annotation_type,
                annotation_collection_name=source_name,
            )
    return root


def test_run_evaluation__object_detection(db_session: Session) -> None:
    root = _create_dataset_with_annotations(db_session)

    result = evaluation_service.run_evaluation(
        session=db_session,
        collection=root,
        task_type=EvaluationTaskType.OBJECT_DETECTION,
        gt_annotation_source="gt",
        pred_annotation_source="pred",
        config=ObjectDetectionEvaluationConfig(iou_threshold=0.7, classwise=False),
        name="run-1",
    )

    assert result.sample_count == 1
    assert result.gt_annotation_count == 1
    assert result.pred_annotation_count == 1
    runs = evaluation_run_resolver.get_all_by_dataset_id(
        session=db_session, dataset_id=root.dataset_id
    )
    assert len(runs) == 1
    assert str(runs[0].id) == str(result.evaluation_run_id)
    assert runs[0].name == "run-1"
    assert runs[0].task_type == EvaluationTaskType.OBJECT_DETECTION
    assert runs[0].config_json == {"iou_threshold": 0.7, "classwise": False}


def test_run_evaluation__generates_default_name(db_session: Session) -> None:
    root = _create_dataset_with_annotations(db_session)

    evaluation_service.run_evaluation(
        session=db_session,
        collection=root,
        task_type=EvaluationTaskType.OBJECT_DETECTION,
        gt_annotation_source="gt",
        pred_annotation_source="pred",
        config=ObjectDetectionEvaluationConfig(),
    )

    runs = evaluation_run_resolver.get_all_by_dataset_id(
        session=db_session, dataset_id=root.dataset_id
    )
    assert runs[0].name.startswith("object_detection ")


def test_run_evaluation__classification(db_session: Session) -> None:
    root = _create_dataset_with_annotations(
        db_session, annotation_type=AnnotationType.CLASSIFICATION
    )

    result = evaluation_service.run_evaluation(
        session=db_session,
        collection=root,
        task_type=EvaluationTaskType.CLASSIFICATION,
        gt_annotation_source="gt",
        pred_annotation_source="pred",
        config=ClassificationEvaluationConfig(),
    )

    assert result.sample_count == 1
    runs = evaluation_run_resolver.get_all_by_dataset_id(
        session=db_session, dataset_id=root.dataset_id
    )
    assert runs[0].task_type == EvaluationTaskType.CLASSIFICATION


def test_run_evaluation__respects_filter(db_session: Session) -> None:
    root = _create_dataset_with_annotations(db_session, image_widths=(1920, 100))

    result = evaluation_service.run_evaluation(
        session=db_session,
        collection=root,
        task_type=EvaluationTaskType.OBJECT_DETECTION,
        gt_annotation_source="gt",
        pred_annotation_source="pred",
        config=ObjectDetectionEvaluationConfig(),
        filters=ImageFilter.model_validate({"filter_type": "image", "width": {"min": 500}}),
    )

    assert result.sample_count == 1


def test_run_evaluation__same_source_raises(db_session: Session) -> None:
    root = _create_dataset_with_annotations(db_session)

    with pytest.raises(ValueError, match="must be different"):
        evaluation_service.run_evaluation(
            session=db_session,
            collection=root,
            task_type=EvaluationTaskType.OBJECT_DETECTION,
            gt_annotation_source="gt",
            pred_annotation_source="gt",
            config=ObjectDetectionEvaluationConfig(),
        )


def test_run_evaluation__wrong_annotation_type_raises(db_session: Session) -> None:
    # Sources hold object-detection annotations, but a classification run is requested.
    root = _create_dataset_with_annotations(db_session)

    with pytest.raises(ValueError, match="classification"):
        evaluation_service.run_evaluation(
            session=db_session,
            collection=root,
            task_type=EvaluationTaskType.CLASSIFICATION,
            gt_annotation_source="gt",
            pred_annotation_source="pred",
            config=ClassificationEvaluationConfig(),
        )


def test_run_evaluation__unknown_source_raises(db_session: Session) -> None:
    root = _create_dataset_with_annotations(db_session)

    with pytest.raises(ValueError, match="not found"):
        evaluation_service.run_evaluation(
            session=db_session,
            collection=root,
            task_type=EvaluationTaskType.OBJECT_DETECTION,
            gt_annotation_source="nonexistent",
            pred_annotation_source="pred",
            config=ObjectDetectionEvaluationConfig(),
        )


def test_run_evaluation__non_image_collection_raises(db_session: Session) -> None:
    root = create_collection(session=db_session)
    annotation_collection = create_collection(
        session=db_session,
        collection_name="annotations",
        parent_collection_id=root.collection_id,
        sample_type=SampleType.ANNOTATION,
    )

    with pytest.raises(ValueError, match="image collections"):
        evaluation_service.run_evaluation(
            session=db_session,
            collection=annotation_collection,
            task_type=EvaluationTaskType.OBJECT_DETECTION,
            gt_annotation_source="gt",
            pred_annotation_source="pred",
            config=ObjectDetectionEvaluationConfig(),
        )
