from __future__ import annotations

from sqlmodel import Session

from lightly_studio.models.evaluation_class_metric import EvaluationClassMetricCreate
from lightly_studio.resolvers import evaluation_class_metric_resolver
from tests.helpers_resolvers import create_annotation_label, create_collection
from tests.resolvers.evaluation_sample_metric_resolver import (
    helpers as evaluation_sample_metric_helpers,
)


def test_delete_by_annotation_label_id(db_session: Session) -> None:
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
                metric_name=metric_name,
                value=0.5,
            )
            for label_id in (cat_id, dog_id)
            for metric_name in ("average_precision", "average_recall")
        ],
    )

    evaluation_class_metric_resolver.delete_by_annotation_label_id(
        session=db_session, annotation_label_id=cat_id
    )
    db_session.commit()

    results = evaluation_class_metric_resolver.get_all_by_evaluation_run_id(
        session=db_session, evaluation_run_id=run.id
    )
    assert sorted((r.annotation_label_id, r.metric_name) for r in results) == sorted(
        [(dog_id, "average_precision"), (dog_id, "average_recall")]
    )
