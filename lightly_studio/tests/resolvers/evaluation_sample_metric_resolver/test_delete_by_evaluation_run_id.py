from __future__ import annotations

import pytest
from sqlmodel import Session

from lightly_studio.models.evaluation_sample_metric import EvaluationSampleMetricCreate
from lightly_studio.resolvers import evaluation_sample_metric_resolver
from tests.helpers_resolvers import create_collection, create_image
from tests.resolvers.evaluation_sample_metric_resolver import (
    helpers as evaluation_sample_metric_helpers,
)


def test_delete_by_evaluation_run_id(db_session: Session) -> None:
    dataset = create_collection(session=db_session)
    run = evaluation_sample_metric_helpers.create_run(
        session=db_session, collection_id=dataset.collection_id
    )
    image = create_image(session=db_session, collection_id=dataset.collection_id)

    evaluation_sample_metric_resolver.create_many(
        session=db_session,
        records=[
            EvaluationSampleMetricCreate(
                evaluation_run_id=run.id,
                sample_id=image.sample_id,
                metric_name="ap",
                value=0.75,
            ),
        ],
    )

    evaluation_sample_metric_resolver.delete_by_evaluation_run_id(
        session=db_session, evaluation_run_id=run.id
    )

    results = evaluation_sample_metric_resolver.get_all_by_evaluation_run_id(
        session=db_session, evaluation_run_id=run.id
    )
    assert results == []


def test_delete_by_evaluation_run_id__does_not_affect_other_runs(
    db_session: Session,
) -> None:
    dataset = create_collection(session=db_session)
    run_to_delete = evaluation_sample_metric_helpers.create_run(
        session=db_session, collection_id=dataset.collection_id, name="run_to_delete"
    )
    run_to_keep = evaluation_sample_metric_helpers.create_run(
        session=db_session, collection_id=dataset.collection_id, name="run_to_keep"
    )
    image = create_image(session=db_session, collection_id=dataset.collection_id)

    evaluation_sample_metric_resolver.create_many(
        session=db_session,
        records=[
            EvaluationSampleMetricCreate(
                evaluation_run_id=run_to_delete.id,
                sample_id=image.sample_id,
                metric_name="ap",
                value=0.5,
            ),
            EvaluationSampleMetricCreate(
                evaluation_run_id=run_to_keep.id,
                sample_id=image.sample_id,
                metric_name="ap",
                value=0.9,
            ),
        ],
    )

    evaluation_sample_metric_resolver.delete_by_evaluation_run_id(
        session=db_session, evaluation_run_id=run_to_delete.id
    )

    deleted_results = evaluation_sample_metric_resolver.get_all_by_evaluation_run_id(
        session=db_session, evaluation_run_id=run_to_delete.id
    )
    assert deleted_results == []

    kept_results = evaluation_sample_metric_resolver.get_all_by_evaluation_run_id(
        session=db_session, evaluation_run_id=run_to_keep.id
    )
    assert len(kept_results) == 1
    assert kept_results[0].value == pytest.approx(0.9)
