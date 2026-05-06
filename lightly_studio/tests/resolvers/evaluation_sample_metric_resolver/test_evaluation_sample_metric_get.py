from __future__ import annotations

import uuid
from uuid import UUID

import pytest
from sqlmodel import Session

from lightly_studio.models.collection import SampleType
from lightly_studio.models.evaluation_run import (
    EvaluationRunCreate,
    EvaluationRunTable,
    EvaluationTaskType,
)
from lightly_studio.models.evaluation_sample_metric import EvaluationSampleMetricTable
from lightly_studio.models.image import ImageTable
from lightly_studio.resolvers import evaluation_run_resolver, evaluation_sample_metric_resolver
from tests.helpers_resolvers import create_collection, create_image


def test_get_all_by_evaluation_run_id(db_session: Session) -> None:
    run, image = _create_run_and_image(db_session)
    _insert_metrics(db_session, run.id, image.sample_id, {"precision": 0.9, "recall": 0.8})

    results = evaluation_sample_metric_resolver.get_all_by_evaluation_run_id(
        session=db_session,
        evaluation_run_id=run.id,
    )

    assert len(results) == 2
    assert all(isinstance(r, EvaluationSampleMetricTable) for r in results)
    assert all(r.evaluation_run_id == run.id for r in results)
    metric_map = {r.metric_name: r.value for r in results}
    assert metric_map == pytest.approx({"precision": 0.9, "recall": 0.8})


def test_get_all_by_evaluation_run_id__returns_empty_for_unknown_run(db_session: Session) -> None:
    results = evaluation_sample_metric_resolver.get_all_by_evaluation_run_id(
        session=db_session,
        evaluation_run_id=uuid.uuid4(),
    )

    assert results == []


def test_get_all_by_evaluation_run_id__excludes_other_runs(db_session: Session) -> None:
    dataset = create_collection(session=db_session)
    run1, image1 = _create_run_and_image(db_session, dataset_collection_id=dataset.collection_id)
    run2, image2 = _create_run_and_image(db_session, dataset_collection_id=dataset.collection_id)
    _insert_metrics(db_session, run1.id, image1.sample_id, {"ap": 0.9})
    _insert_metrics(db_session, run2.id, image2.sample_id, {"ap": 0.5})

    results = evaluation_sample_metric_resolver.get_all_by_evaluation_run_id(
        session=db_session,
        evaluation_run_id=run1.id,
    )

    assert len(results) == 1
    assert results[0].evaluation_run_id == run1.id
    assert results[0].sample_id == image1.sample_id


def _create_run_and_image(
    session: Session,
    dataset_collection_id: UUID | None = None,
) -> tuple[EvaluationRunTable, ImageTable]:
    if dataset_collection_id is None:
        dataset_collection_id = create_collection(session=session).collection_id
    gt_collection = create_collection(
        session=session,
        sample_type=SampleType.ANNOTATION,
        parent_collection_id=dataset_collection_id,
    )
    pred_collection = create_collection(
        session=session,
        sample_type=SampleType.ANNOTATION,
        parent_collection_id=dataset_collection_id,
    )
    run = evaluation_run_resolver.create(
        session=session,
        evaluation_run_input=EvaluationRunCreate(
            name="test_run",
            gt_annotation_collection_id=gt_collection.collection_id,
            pred_annotation_collection_id=pred_collection.collection_id,
            task_type=EvaluationTaskType.OBJECT_DETECTION,
        ),
    )
    image = create_image(session=session, collection_id=dataset_collection_id)
    return run, image


def _insert_metrics(
    session: Session,
    evaluation_run_id: UUID,
    sample_id: UUID,
    metrics: dict[str, float],
) -> None:
    evaluation_sample_metric_resolver.create_many(
        session=session,
        records=[
            EvaluationSampleMetricTable(
                evaluation_run_id=evaluation_run_id,
                sample_id=sample_id,
                metric_name=name,
                value=value,
            )
            for name, value in metrics.items()
        ],
    )
