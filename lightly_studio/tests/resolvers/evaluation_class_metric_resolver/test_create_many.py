from __future__ import annotations

import pytest
from sqlmodel import Session

from lightly_studio.models.evaluation_class_metric import EvaluationClassMetricCreate
from lightly_studio.resolvers import evaluation_class_metric_resolver
from tests.helpers_resolvers import create_annotation_label, create_collection
from tests.resolvers.evaluation_sample_metric_resolver import (
    helpers as evaluation_sample_metric_helpers,
)


def test_create_many(db_session: Session) -> None:
    dataset = create_collection(session=db_session)
    run = evaluation_sample_metric_helpers.create_run(
        session=db_session, collection_id=dataset.collection_id
    )
    cat = create_annotation_label(
        session=db_session, root_collection_id=dataset.collection_id, label_name="cat"
    )
    dog = create_annotation_label(
        session=db_session, root_collection_id=dataset.collection_id, label_name="dog"
    )

    evaluation_class_metric_resolver.create_many(
        session=db_session,
        records=[
            EvaluationClassMetricCreate(
                evaluation_run_id=run.id,
                annotation_label_id=cat.annotation_label_id,
                metric_name="average_precision",
                value=0.75,
            ),
            EvaluationClassMetricCreate(
                evaluation_run_id=run.id,
                annotation_label_id=dog.annotation_label_id,
                metric_name="average_precision",
                value=0.60,
            ),
        ],
    )

    results = evaluation_class_metric_resolver.get_all_by_evaluation_run_id(
        session=db_session,
        evaluation_run_id=run.id,
    )
    values = {(r.annotation_label_id, r.metric_name): r.value for r in results}
    assert values == pytest.approx(
        {
            (cat.annotation_label_id, "average_precision"): 0.75,
            (dog.annotation_label_id, "average_precision"): 0.60,
        }
    )


def test_create_many__empty_list_is_noop(db_session: Session) -> None:
    run = evaluation_sample_metric_helpers.create_run(session=db_session)

    evaluation_class_metric_resolver.create_many(session=db_session, records=[])

    results = evaluation_class_metric_resolver.get_all_by_evaluation_run_id(
        session=db_session,
        evaluation_run_id=run.id,
    )
    assert results == []
