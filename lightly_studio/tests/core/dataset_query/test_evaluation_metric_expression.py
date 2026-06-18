from __future__ import annotations

from uuid import uuid4

import pytest
from sqlmodel import Session, select

from lightly_studio.core.dataset_query.dataset_query import DatasetQuery
from lightly_studio.core.dataset_query.evaluation_metric_expression import EvaluationMetricField
from lightly_studio.core.dataset_query.match_expression import MatchExpression
from lightly_studio.models.collection import SampleType
from lightly_studio.models.evaluation_run import (
    EvaluationRunCreate,
    EvaluationTaskType,
)
from lightly_studio.models.evaluation_sample_metric import EvaluationSampleMetricCreate
from lightly_studio.models.image import ImageTable
from lightly_studio.resolvers import (
    evaluation_run_resolver,
    evaluation_sample_metric_resolver,
)
from tests.helpers_resolvers import create_collection, create_image


def test_evaluation_metric_field__sql() -> None:
    query = (
        select(ImageTable)
        .join(ImageTable.sample)
        .where((EvaluationMetricField(evaluation_run_id=uuid4(), metric_name="score") >= 0.5).get())
    )
    sql = str(query.compile(compile_kwargs={"literal_binds": True})).lower()

    assert "exists (select 1" in sql
    assert "from evaluation_sample_metric" in sql
    assert "join evaluation_run" not in sql
    assert "from evaluation_run" not in sql
    assert ", sample" not in sql
    assert "join sample" in sql
    assert "evaluation_sample_metric.evaluation_run_id =" in sql
    assert "evaluation_sample_metric.metric_name = 'score'" in sql
    assert "evaluation_sample_metric.value >= 0.5" in sql


@pytest.mark.parametrize(
    ("expression", "expected_sql"),
    [
        (
            EvaluationMetricField(evaluation_run_id=uuid4(), metric_name="score") > 0.5,
            "evaluation_sample_metric.value > 0.5",
        ),
        (
            EvaluationMetricField(evaluation_run_id=uuid4(), metric_name="score") >= 0.5,
            "evaluation_sample_metric.value >= 0.5",
        ),
        (
            EvaluationMetricField(evaluation_run_id=uuid4(), metric_name="score") < 0.5,
            "evaluation_sample_metric.value < 0.5",
        ),
        (
            EvaluationMetricField(evaluation_run_id=uuid4(), metric_name="score") <= 0.5,
            "evaluation_sample_metric.value <= 0.5",
        ),
        (
            EvaluationMetricField(evaluation_run_id=uuid4(), metric_name="score") == 0.5,
            "evaluation_sample_metric.value = 0.5",
        ),
        (
            EvaluationMetricField(evaluation_run_id=uuid4(), metric_name="score") != 0.5,
            "evaluation_sample_metric.value != 0.5",
        ),
    ],
)
def test_evaluation_metric_field__operators(expression: MatchExpression, expected_sql: str) -> None:
    query = select(ImageTable).join(ImageTable.sample).where(expression.get())
    sql = str(query.compile(compile_kwargs={"literal_binds": True})).lower()

    assert expected_sql in sql


def test_evaluation_metric_field__filters_matching_samples(db_session: Session) -> None:
    dataset = create_collection(session=db_session)
    collection_id = dataset.collection_id
    image_a = create_image(
        session=db_session, collection_id=collection_id, file_path_abs="/path/to/a.jpg"
    )
    image_b = create_image(
        session=db_session, collection_id=collection_id, file_path_abs="/path/to/b.jpg"
    )
    gt_collection = create_collection(
        session=db_session,
        parent_collection_id=collection_id,
        sample_type=SampleType.ANNOTATION,
    )
    pred_collection = create_collection(
        session=db_session,
        parent_collection_id=collection_id,
        sample_type=SampleType.ANNOTATION,
    )
    run = evaluation_run_resolver.create(
        session=db_session,
        evaluation_run_input=EvaluationRunCreate(
            name="run1",
            gt_annotation_collection_id=gt_collection.collection_id,
            dataset_id=gt_collection.dataset_id,
            pred_annotation_collection_id=pred_collection.collection_id,
            task_type=EvaluationTaskType.OBJECT_DETECTION,
        ),
    )
    evaluation_sample_metric_resolver.create_many(
        session=db_session,
        records=[
            EvaluationSampleMetricCreate(
                evaluation_run_id=run.id,
                sample_id=image_a.sample_id,
                metric_name="score",
                value=0.2,
            ),
            EvaluationSampleMetricCreate(
                evaluation_run_id=run.id,
                sample_id=image_b.sample_id,
                metric_name="score",
                value=0.9,
            ),
        ],
    )

    results = (
        DatasetQuery(dataset=dataset, session=db_session)
        .match(EvaluationMetricField(evaluation_run_id=run.id, metric_name="score") > 0.5)
        .to_list()
    )

    assert [result.sample_id for result in results] == [image_b.sample_id]
