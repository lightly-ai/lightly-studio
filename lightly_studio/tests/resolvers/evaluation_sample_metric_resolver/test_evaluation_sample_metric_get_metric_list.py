from __future__ import annotations

import uuid

import pytest
from sqlmodel import Session

from lightly_studio.models.evaluation_sample_metric import EvaluationSampleMetricBoundsView
from lightly_studio.resolvers import evaluation_sample_metric_resolver
from tests.helpers_resolvers import create_collection, create_image
from tests.resolvers.evaluation_sample_metric_resolver import (
    helpers as evaluation_sample_metric_helpers,
)


def test_get_metric_list_by_evaluation_run_id(db_session: Session) -> None:
    dataset = create_collection(session=db_session)
    run, image1 = evaluation_sample_metric_helpers.create_run_and_image(
        session=db_session, dataset_collection_id=dataset.collection_id
    )
    image2 = create_image(
        session=db_session,
        collection_id=dataset.collection_id,
        file_path_abs="/path/to/sample2.png",
    )
    evaluation_sample_metric_helpers.insert_metrics(
        session=db_session,
        evaluation_run_id=run.id,
        sample_id=image1.sample_id,
        metrics={"precision": 0.9, "recall": 0.7},
    )
    evaluation_sample_metric_helpers.insert_metrics(
        session=db_session,
        evaluation_run_id=run.id,
        sample_id=image2.sample_id,
        metrics={"precision": 0.6, "recall": 0.8},
    )

    results = evaluation_sample_metric_resolver.get_metric_list_by_evaluation_run_id(
        session=db_session,
        evaluation_run_id=run.id,
    )

    assert len(results) == 2
    assert all(isinstance(r, EvaluationSampleMetricBoundsView) for r in results)
    bounds = {r.metric_name: r for r in results}
    assert bounds["precision"].min_value == pytest.approx(0.6)
    assert bounds["precision"].max_value == pytest.approx(0.9)
    assert bounds["recall"].min_value == pytest.approx(0.7)
    assert bounds["recall"].max_value == pytest.approx(0.8)


def test_get_metric_list_by_evaluation_run_id__single_sample(db_session: Session) -> None:
    run, image = evaluation_sample_metric_helpers.create_run_and_image(session=db_session)
    evaluation_sample_metric_helpers.insert_metrics(
        session=db_session,
        evaluation_run_id=run.id,
        sample_id=image.sample_id,
        metrics={"ap": 0.75},
    )

    results = evaluation_sample_metric_resolver.get_metric_list_by_evaluation_run_id(
        session=db_session,
        evaluation_run_id=run.id,
    )

    assert len(results) == 1
    assert results[0].metric_name == "ap"
    assert results[0].min_value == pytest.approx(0.75)
    assert results[0].max_value == pytest.approx(0.75)


def test_get_metric_list_by_evaluation_run_id__returns_empty_for_unknown_run(
    db_session: Session,
) -> None:
    results = evaluation_sample_metric_resolver.get_metric_list_by_evaluation_run_id(
        session=db_session,
        evaluation_run_id=uuid.uuid4(),
    )

    assert results == []


def test_get_metric_list_by_evaluation_run_id__excludes_other_runs(db_session: Session) -> None:
    dataset = create_collection(session=db_session)
    run1, image1 = evaluation_sample_metric_helpers.create_run_and_image(
        session=db_session, dataset_collection_id=dataset.collection_id, name="run1"
    )
    run2, image2 = evaluation_sample_metric_helpers.create_run_and_image(
        session=db_session, dataset_collection_id=dataset.collection_id, name="run2"
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
        metrics={"ap": 0.1},
    )

    results = evaluation_sample_metric_resolver.get_metric_list_by_evaluation_run_id(
        session=db_session,
        evaluation_run_id=run1.id,
    )

    assert len(results) == 1
    assert results[0].metric_name == "ap"
    assert results[0].min_value == pytest.approx(0.9)
    assert results[0].max_value == pytest.approx(0.9)
