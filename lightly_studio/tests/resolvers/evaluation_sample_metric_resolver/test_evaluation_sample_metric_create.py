from __future__ import annotations

from sqlmodel import Session

from lightly_studio.models.evaluation_sample_metric import EvaluationSampleMetricCreate
from lightly_studio.resolvers import evaluation_sample_metric_resolver
from tests.helpers_resolvers import create_collection, create_image
from tests.resolvers.evaluation_sample_metric_resolver import (
    helpers as evaluation_sample_metric_helpers,
)


def test_create_many(db_session: Session) -> None:
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

    evaluation_sample_metric_resolver.create_many(
        session=db_session,
        records=[
            EvaluationSampleMetricCreate(
                evaluation_run_id=run.id,
                sample_id=image1.sample_id,
                metric_name="ap",
                value=0.75,
            ),
            EvaluationSampleMetricCreate(
                evaluation_run_id=run.id,
                sample_id=image2.sample_id,
                metric_name="ap",
                value=0.60,
            ),
        ],
    )

    results = evaluation_sample_metric_resolver.get_all_by_evaluation_run_id(
        session=db_session,
        evaluation_run_id=run.id,
    )
    assert len(results) == 2
    sample_ids = {r.sample_id for r in results}
    assert sample_ids == {image1.sample_id, image2.sample_id}


def test_create_many__empty_list_is_noop(db_session: Session) -> None:
    run = evaluation_sample_metric_helpers.create_run(session=db_session)

    evaluation_sample_metric_resolver.create_many(session=db_session, records=[])

    results = evaluation_sample_metric_resolver.get_all_by_evaluation_run_id(
        session=db_session,
        evaluation_run_id=run.id,
    )
    assert results == []
