from __future__ import annotations

import uuid

import pytest
from sqlmodel import Session

from lightly_studio.models.evaluation_sample_metric import EvaluationRunMetricsInfoView
from lightly_studio.resolvers import evaluation_sample_metric_resolver
from tests.helpers_resolvers import create_collection, create_image
from tests.resolvers.evaluation_sample_metric_resolver import (
    helpers as evaluation_sample_metric_helpers,
)
from tests.resolvers.evaluation_sample_metric_resolver.helpers import SampleMetricStub


def test_get_sample_metrics_info_by_dataset_id(db_session: Session) -> None:
    dataset = create_collection(session=db_session)
    run = evaluation_sample_metric_helpers.create_run(
        session=db_session, collection_id=dataset.collection_id
    )
    image1 = create_image(session=db_session, collection_id=dataset.collection_id)
    image2 = create_image(
        session=db_session,
        collection_id=dataset.collection_id,
        file_path_abs="/path/to/sample2.png",
    )
    evaluation_sample_metric_helpers.create_sample_metrics(
        session=db_session,
        run_id=run.id,
        sample_metrics=[
            SampleMetricStub(
                sample_id=image1.sample_id,
                metrics={"precision": 0.9, "recall": 0.7},
            )
        ],
    )
    evaluation_sample_metric_helpers.create_sample_metrics(
        session=db_session,
        run_id=run.id,
        sample_metrics=[
            SampleMetricStub(
                sample_id=image2.sample_id,
                metrics={"precision": 0.6, "recall": 0.8},
            )
        ],
    )

    results = evaluation_sample_metric_resolver.get_sample_metrics_info_by_dataset_id(
        session=db_session,
        dataset_id=dataset.dataset_id,
    )

    assert len(results) == 1
    assert isinstance(results[0], EvaluationRunMetricsInfoView)
    assert results[0].run_name == run.name
    bounds = {m.metric_name: m for m in results[0].metrics}
    assert bounds["precision"].min_value == pytest.approx(0.6)
    assert bounds["precision"].max_value == pytest.approx(0.9)
    assert bounds["recall"].min_value == pytest.approx(0.7)
    assert bounds["recall"].max_value == pytest.approx(0.8)


def test_get_sample_metrics_info_by_dataset_id__multiple_runs(db_session: Session) -> None:
    dataset = create_collection(session=db_session)
    run1 = evaluation_sample_metric_helpers.create_run(
        session=db_session, collection_id=dataset.collection_id, name="run_1"
    )
    image1 = create_image(
        session=db_session,
        collection_id=dataset.collection_id,
        file_path_abs="/path/to/sample1.png",
    )
    run2 = evaluation_sample_metric_helpers.create_run(
        session=db_session, collection_id=dataset.collection_id, name="run_2"
    )
    image2 = create_image(
        session=db_session,
        collection_id=dataset.collection_id,
        file_path_abs="/path/to/sample2.png",
    )
    evaluation_sample_metric_helpers.create_sample_metrics(
        session=db_session,
        run_id=run1.id,
        sample_metrics=[SampleMetricStub(sample_id=image1.sample_id, metrics={"ap": 0.9})],
    )
    evaluation_sample_metric_helpers.create_sample_metrics(
        session=db_session,
        run_id=run2.id,
        sample_metrics=[
            SampleMetricStub(sample_id=image2.sample_id, metrics={"ap": 0.5, "ar": 0.4})
        ],
    )

    results = evaluation_sample_metric_resolver.get_sample_metrics_info_by_dataset_id(
        session=db_session,
        dataset_id=dataset.dataset_id,
    )

    assert len(results) == 2
    by_name = {r.run_name: r for r in results}
    assert set(by_name.keys()) == {run1.name, run2.name}

    run1_bounds = {m.metric_name: m for m in by_name[run1.name].metrics}
    assert len(run1_bounds) == 1
    assert run1_bounds["ap"].min_value == pytest.approx(0.9)
    assert run1_bounds["ap"].max_value == pytest.approx(0.9)

    run2_bounds = {m.metric_name: m for m in by_name[run2.name].metrics}
    assert len(run2_bounds) == 2
    assert run2_bounds["ap"].min_value == pytest.approx(0.5)
    assert run2_bounds["ap"].max_value == pytest.approx(0.5)
    assert run2_bounds["ar"].min_value == pytest.approx(0.4)
    assert run2_bounds["ar"].max_value == pytest.approx(0.4)


def test_get_sample_metrics_info_by_dataset_id__excludes_other_datasets(
    db_session: Session,
) -> None:
    dataset = create_collection(session=db_session)
    other_dataset = create_collection(session=db_session)
    run = evaluation_sample_metric_helpers.create_run(
        session=db_session, collection_id=dataset.collection_id
    )
    image = create_image(session=db_session, collection_id=dataset.collection_id)
    other_run = evaluation_sample_metric_helpers.create_run(
        session=db_session, collection_id=other_dataset.collection_id
    )
    other_image = create_image(session=db_session, collection_id=other_dataset.collection_id)
    evaluation_sample_metric_helpers.create_sample_metrics(
        session=db_session,
        run_id=run.id,
        sample_metrics=[SampleMetricStub(sample_id=image.sample_id, metrics={"ap": 0.9})],
    )
    evaluation_sample_metric_helpers.create_sample_metrics(
        session=db_session,
        run_id=other_run.id,
        sample_metrics=[SampleMetricStub(sample_id=other_image.sample_id, metrics={"ap": 0.1})],
    )

    results = evaluation_sample_metric_resolver.get_sample_metrics_info_by_dataset_id(
        session=db_session,
        dataset_id=dataset.dataset_id,
    )

    assert len(results) == 1
    assert results[0].run_name == run.name


def test_get_sample_metrics_info_by_dataset_id__empty_for_unknown_dataset(
    db_session: Session,
) -> None:
    results = evaluation_sample_metric_resolver.get_sample_metrics_info_by_dataset_id(
        session=db_session,
        dataset_id=uuid.uuid4(),
    )

    assert results == []


def test_get_sample_metrics_info_by_dataset_id__empty_for_run_without_metrics(
    db_session: Session,
) -> None:
    dataset = create_collection(session=db_session)
    # Create a run but add no metrics.
    evaluation_sample_metric_helpers.create_run(
        session=db_session, collection_id=dataset.collection_id
    )

    results = evaluation_sample_metric_resolver.get_sample_metrics_info_by_dataset_id(
        session=db_session,
        dataset_id=dataset.dataset_id,
    )

    assert results == []
