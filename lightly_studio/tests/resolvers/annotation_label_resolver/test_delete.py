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
    cat = create_annotation_label(
        session=db_session, root_collection_id=dataset.collection_id, label_name="cat"
    )
    dog = create_annotation_label(
        session=db_session, root_collection_id=dataset.collection_id, label_name="dog"
    )
    cat_id = cat.annotation_label_id
    dog_id = dog.annotation_label_id
    evaluation_class_metric_resolver.create_many(
        session=db_session,
        records=[
            EvaluationClassMetricCreate(
                evaluation_run_id=run.id,
                annotation_label_id=label_id,
                metric_name="average_precision",
                value=0.5,
            )
            for label_id in (cat_id, dog_id)
        ],
    )

    assert annotation_label_resolver.delete(session=db_session, label_id=cat_id)

    assert annotation_label_resolver.get_by_id(session=db_session, label_id=cat_id) is None
    metrics = evaluation_class_metric_resolver.get_all_by_evaluation_run_id(
        session=db_session, evaluation_run_id=run.id
    )
    assert [metric.annotation_label_id for metric in metrics] == [dog_id]
