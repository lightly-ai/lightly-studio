from __future__ import annotations

from uuid import UUID

import pytest
from sqlmodel import Session

from lightly_studio.evaluation import run_metrics
from lightly_studio.evaluation.image_dataset_evaluate import ObjectDetectionEvaluationConfig
from lightly_studio.models.annotation.annotation_base import AnnotationType
from lightly_studio.models.collection import SampleType
from lightly_studio.models.evaluation_annotation_metric import EvaluationAnnotationMetricCreate
from lightly_studio.models.evaluation_run import (
    EvaluationRunCreate,
    EvaluationRunTable,
    EvaluationTaskType,
)
from lightly_studio.resolvers import (
    evaluation_annotation_metric_resolver,
    evaluation_run_resolver,
    tag_resolver,
)
from lightly_studio.services import evaluation_service
from tests.api.routes.api.evaluation import helpers
from tests.helpers_resolvers import (
    create_annotation,
    create_annotation_label,
    create_collection,
    create_image,
    create_tag,
)

MASK_DATA = {"x": 0, "y": 0, "width": 2, "height": 2, "segmentation_mask": [0, 4]}


def test_compute_run_metrics__instance_segmentation(db_session: Session) -> None:
    # One true positive and one false positive: precision 1/2, recall 1/1.
    run, dataset_collection_id = _create_run(
        session=db_session, task_type=EvaluationTaskType.INSTANCE_SEGMENTATION
    )
    image = create_image(session=db_session, collection_id=dataset_collection_id, width=2, height=2)
    label = create_annotation_label(
        session=db_session, root_collection_id=dataset_collection_id, label_name="cat"
    )
    annotation_ids: dict[str, UUID] = {}
    for name, source in (("gt", "gt"), ("pred_tp", "pred"), ("pred_fp", "pred")):
        annotation_ids[name] = create_annotation(
            session=db_session,
            collection_id=dataset_collection_id,
            sample_id=image.sample_id,
            annotation_label_id=label.annotation_label_id,
            annotation_type=AnnotationType.SEGMENTATION_MASK,
            annotation_data=MASK_DATA,
            annotation_collection_name=source,
        ).sample_id
    evaluation_annotation_metric_resolver.create_many(
        session=db_session,
        records=[
            EvaluationAnnotationMetricCreate(
                evaluation_run_id=run.id,
                sample_id=image.sample_id,
                gt_annotation_id=annotation_ids["gt"],
                pred_annotation_id=annotation_ids["pred_tp"],
            ),
            EvaluationAnnotationMetricCreate(
                evaluation_run_id=run.id,
                sample_id=image.sample_id,
                pred_annotation_id=annotation_ids["pred_fp"],
            ),
        ],
    )

    metrics = run_metrics.compute_run_metrics(session=db_session, evaluation_run=run)

    assert metrics.precision == pytest.approx(0.5)
    assert metrics.recall == pytest.approx(1.0)
    assert metrics.accuracy is None
    assert metrics.mean_average_precision is None


def test_compute_run_metrics__semantic_segmentation_raises(db_session: Session) -> None:
    run, _ = _create_run(session=db_session, task_type=EvaluationTaskType.SEMANTIC_SEGMENTATION)

    with pytest.raises(NotImplementedError, match="semantic_segmentation"):
        run_metrics.compute_run_metrics(session=db_session, evaluation_run=run)


def test_compute_slice_metrics(db_session: Session) -> None:
    # The full run has one hit and one miss. The slice holds only the hit image.
    run, tag_id = _create_hit_and_miss_run(
        session=db_session, compute_average_precision=True, tagged_images=("hit",)
    )

    full = run_metrics.compute_run_metrics(session=db_session, evaluation_run=run)
    tagged = run_metrics.compute_slice_metrics(
        session=db_session, evaluation_run=run, tag_id=tag_id
    )

    assert full.precision == pytest.approx(0.5)
    assert tagged.precision == pytest.approx(1.0)
    assert tagged.recall == pytest.approx(1.0)
    assert tagged.mean_average_precision == pytest.approx(1.0)


def test_compute_slice_metrics__run_without_average_precision(db_session: Session) -> None:
    run, tag_id = _create_hit_and_miss_run(
        session=db_session, compute_average_precision=False, tagged_images=("hit",)
    )

    tagged = run_metrics.compute_slice_metrics(
        session=db_session, evaluation_run=run, tag_id=tag_id
    )

    assert tagged.precision == pytest.approx(1.0)
    assert tagged.mean_average_precision is None


def test_compute_slice_metrics__tag_without_evaluated_images(db_session: Session) -> None:
    run, tag_id = _create_hit_and_miss_run(
        session=db_session, compute_average_precision=True, tagged_images=()
    )

    tagged = run_metrics.compute_slice_metrics(
        session=db_session, evaluation_run=run, tag_id=tag_id
    )

    assert tagged.per_class == []
    assert tagged.precision == 0.0
    assert tagged.mean_average_precision is None


def _create_hit_and_miss_run(
    session: Session, compute_average_precision: bool, tagged_images: tuple[str, ...]
) -> tuple[EvaluationRunTable, UUID]:
    """Evaluate the hit-and-miss dataset and tag the named images ("hit", "miss")."""
    root, hit_id, miss_id = helpers.create_dataset_with_hit_and_miss(db_session=session)
    result = evaluation_service.run_evaluation(
        session=session,
        collection=root,
        task_type=EvaluationTaskType.OBJECT_DETECTION,
        gt_annotation_source="gt",
        pred_annotation_source="pred",
        config=ObjectDetectionEvaluationConfig(compute_average_precision=compute_average_precision),
        name="run-1",
    )
    tag = create_tag(session=session, collection_id=root.collection_id, tag_name="slice")
    sample_ids = {"hit": hit_id, "miss": miss_id}
    tag_resolver.add_sample_ids_to_tag_id(
        session=session,
        tag_id=tag.tag_id,
        sample_ids=[sample_ids[name] for name in tagged_images],
    )
    run = evaluation_run_resolver.get_by_id(session=session, evaluation_id=result.evaluation_run_id)
    assert run is not None
    return run, tag.tag_id


def _create_run(session: Session, task_type: EvaluationTaskType) -> tuple[EvaluationRunTable, UUID]:
    """Create a run with "gt" and "pred" sources. Return it with its root collection ID."""
    dataset = create_collection(session=session)
    sources = {
        name: create_collection(
            session=session,
            collection_name=name,
            parent_collection_id=dataset.collection_id,
            sample_type=SampleType.ANNOTATION,
        )
        for name in ("gt", "pred")
    }
    run = evaluation_run_resolver.create(
        session=session,
        evaluation_run_input=EvaluationRunCreate(
            name="run_1",
            gt_annotation_collection_id=sources["gt"].collection_id,
            pred_annotation_collection_id=sources["pred"].collection_id,
            dataset_id=dataset.dataset_id,
            task_type=task_type,
        ),
    )
    return run, dataset.collection_id
