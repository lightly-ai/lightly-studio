from __future__ import annotations

import pytest
from sqlmodel import Session

from lightly_studio.models.evaluation_class_metric import EvaluationClassMetricCreate
from lightly_studio.resolvers import evaluation_class_metric_resolver
from tests.helpers_resolvers import create_annotation_label, create_collection
from tests.resolvers.evaluation_sample_metric_resolver import (
    helpers as evaluation_sample_metric_helpers,
)


def test_delete_by_evaluation_run_id__does_not_affect_other_runs(db_session: Session) -> None:
    dataset = create_collection(session=db_session)
    run_to_delete = evaluation_sample_metric_helpers.create_run(
        session=db_session, collection_id=dataset.collection_id, name="run_to_delete"
    )
    run_to_keep = evaluation_sample_metric_helpers.create_run(
        session=db_session, collection_id=dataset.collection_id, name="run_to_keep"
    )
    label = create_annotation_label(session=db_session, root_collection_id=dataset.collection_id)
    evaluation_class_metric_resolver.create_many(
        session=db_session,
        records=[
            EvaluationClassMetricCreate(
                evaluation_run_id=run_to_delete.id,
                annotation_label_id=label.annotation_label_id,
                metric_name="average_precision",
                value=0.5,
            ),
            EvaluationClassMetricCreate(
                evaluation_run_id=run_to_keep.id,
                annotation_label_id=label.annotation_label_id,
                metric_name="average_precision",
                value=0.9,
            ),
        ],
    )

    evaluation_class_metric_resolver.delete_by_evaluation_run_id(
        session=db_session, evaluation_run_id=run_to_delete.id
    )

    assert (
        evaluation_class_metric_resolver.get_all_by_evaluation_run_id(
            session=db_session, evaluation_run_id=run_to_delete.id
        )
        == []
    )
    kept_results = evaluation_class_metric_resolver.get_all_by_evaluation_run_id(
        session=db_session, evaluation_run_id=run_to_keep.id
    )
    assert len(kept_results) == 1
    assert kept_results[0].value == pytest.approx(0.9)
