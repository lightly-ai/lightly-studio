from __future__ import annotations

import uuid

import pytest
from sqlmodel import Session

from lightly_studio.models.evaluation_sample_metric import EvaluationSampleMetricTable
from lightly_studio.resolvers import evaluation_sample_metric_resolver
from tests.helpers_resolvers import create_collection
from tests.resolvers.evaluation_sample_metric_resolver import (
    helpers as evaluation_sample_metric_helpers,
)


def test_get_all_by_evaluation_run_id(db_session: Session) -> None:
    run, image = evaluation_sample_metric_helpers.create_run_and_image(session=db_session)
    evaluation_sample_metric_helpers.insert_metrics(
        session=db_session,
        evaluation_run_id=run.id,
        sample_id=image.sample_id,
        metrics={"precision": 0.9, "recall": 0.8},
    )

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
    run1, image1 = evaluation_sample_metric_helpers.create_run_and_image(
        session=db_session, dataset_collection_id=dataset.collection_id
    )
    run2, image2 = evaluation_sample_metric_helpers.create_run_and_image(
        session=db_session, dataset_collection_id=dataset.collection_id
    )
    evaluation_sample_metric_helpers.insert_metrics(
        session=db_session,
        evaluation_run_id=run1.id,
        sample_id=image1.sample_id,
        metrics={"ap": 0.9},
    )
    evaluation_sample_metric_helpers.insert_metrics(
        session=db_session,
        evaluation_run_id=run2.id,
        sample_id=image2.sample_id,
        metrics={"ap": 0.5},
    )

    results = evaluation_sample_metric_resolver.get_all_by_evaluation_run_id(
        session=db_session,
        evaluation_run_id=run1.id,
    )

    assert len(results) == 1
    assert results[0].evaluation_run_id == run1.id
    assert results[0].sample_id == image1.sample_id
    assert results[0].value == pytest.approx(0.9)
