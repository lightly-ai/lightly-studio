from __future__ import annotations

import uuid

import pytest
from sqlmodel import Session

from lightly_studio.models.evaluation_class_metric import EvaluationClassMetricCreate
from lightly_studio.resolvers import evaluation_class_metric_resolver
from tests.helpers_resolvers import create_annotation_label, create_collection
from tests.resolvers.evaluation_sample_metric_resolver import (
    helpers as evaluation_sample_metric_helpers,
)


def test_get_all_by_evaluation_run_id__returns_empty_for_unknown_run(db_session: Session) -> None:
    results = evaluation_class_metric_resolver.get_all_by_evaluation_run_id(
        session=db_session,
        evaluation_run_id=uuid.uuid4(),
    )

    assert results == []


def test_get_all_by_evaluation_run_id__excludes_other_runs(db_session: Session) -> None:
    dataset = create_collection(session=db_session)
    run1 = evaluation_sample_metric_helpers.create_run(
        session=db_session, collection_id=dataset.collection_id, name="run1"
    )
    run2 = evaluation_sample_metric_helpers.create_run(
        session=db_session, collection_id=dataset.collection_id, name="run2"
    )
    label = create_annotation_label(session=db_session, root_collection_id=dataset.collection_id)
    evaluation_class_metric_resolver.create_many(
        session=db_session,
        records=[
            EvaluationClassMetricCreate(
                evaluation_run_id=run1.id,
                annotation_label_id=label.annotation_label_id,
                metric_name="average_precision",
                value=0.9,
            ),
            EvaluationClassMetricCreate(
                evaluation_run_id=run2.id,
                annotation_label_id=label.annotation_label_id,
                metric_name="average_precision",
                value=0.5,
            ),
        ],
    )

    results = evaluation_class_metric_resolver.get_all_by_evaluation_run_id(
        session=db_session,
        evaluation_run_id=run1.id,
    )

    assert len(results) == 1
    assert results[0].evaluation_run_id == run1.id
    assert results[0].value == pytest.approx(0.9)
