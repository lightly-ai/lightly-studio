from __future__ import annotations

from sqlmodel import Session

from lightly_studio.models.evaluation_class_metric import EvaluationClassMetricCreate
from lightly_studio.resolvers import annotation_label_resolver, evaluation_class_metric_resolver
from tests.helpers_resolvers import create_annotation_label, create_collection
from tests.resolvers.evaluation_sample_metric_resolver import (
    helpers as evaluation_sample_metric_helpers,
)


def test_delete__label_with_class_metrics(db_session: Session) -> None:
    dataset = create_collection(session=db_session)
    run = evaluation_sample_metric_helpers.create_run(
        session=db_session, collection_id=dataset.collection_id
    )
    label = create_annotation_label(session=db_session, root_collection_id=dataset.collection_id)
    evaluation_class_metric_resolver.create_many(
        session=db_session,
        records=[
            EvaluationClassMetricCreate(
                evaluation_run_id=run.id,
                annotation_label_id=label.annotation_label_id,
                metric_name="average_precision@0.50",
                value=0.5,
            )
        ],
    )

    # Class metrics do not block deleting the label.
    assert annotation_label_resolver.delete(session=db_session, label_id=label.annotation_label_id)
    assert (
        annotation_label_resolver.get_by_id(session=db_session, label_id=label.annotation_label_id)
        is None
    )
