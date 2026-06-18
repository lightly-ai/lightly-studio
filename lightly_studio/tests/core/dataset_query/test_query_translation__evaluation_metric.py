from __future__ import annotations

import pytest
from sqlmodel import Session

from lightly_studio.core.dataset_query import query_translation
from lightly_studio.core.dataset_query.dataset_query import DatasetQuery
from lightly_studio.errors import QueryExprError
from lightly_studio.models.collection import SampleType
from lightly_studio.models.evaluation_run import (
    EvaluationRunCreate,
    EvaluationTaskType,
)
from lightly_studio.models.evaluation_sample_metric import EvaluationSampleMetricCreate
from lightly_studio.models.query_expr import (
    AndExpr,
    ClassificationMatchExpr,
    EvaluationMetricExpr,
    ObjectDetectionMatchExpr,
    OrdinalComparisonOperator,
    SegmentationMaskMatchExpr,
)
from lightly_studio.resolvers import (
    evaluation_run_resolver,
    evaluation_sample_metric_resolver,
)
from tests.helpers_resolvers import create_collection, create_image


def test_to_match_expression__evaluation_metric_sql() -> None:
    expr = EvaluationMetricExpr(
        evaluation_run_name="run1",
        metric_name="miou",
        operator=OrdinalComparisonOperator.LT,
        value=0.3,
    )

    sql = str(
        query_translation.to_match_expression(expr)
        .get()
        .compile(compile_kwargs={"literal_binds": True})
    ).lower()
    assert "exists (select 1" in sql
    assert "join evaluation_run" in sql
    assert "evaluation_run.name = 'run1'" in sql
    assert "evaluation_sample_metric.metric_name = 'miou'" in sql
    assert "evaluation_sample_metric.value < 0.3" in sql


def test_to_match_expression__evaluation_metric_db(db_session: Session) -> None:
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
            name="semseg-eval",
            gt_annotation_collection_id=gt_collection.collection_id,
            dataset_id=gt_collection.dataset_id,
            pred_annotation_collection_id=pred_collection.collection_id,
            task_type=EvaluationTaskType.SEMANTIC_SEGMENTATION,
        ),
    )
    evaluation_sample_metric_resolver.create_many(
        session=db_session,
        records=[
            EvaluationSampleMetricCreate(
                evaluation_run_id=run.id,
                sample_id=image_a.sample_id,
                metric_name="miou",
                value=0.2,
            ),
            EvaluationSampleMetricCreate(
                evaluation_run_id=run.id,
                sample_id=image_b.sample_id,
                metric_name="miou",
                value=0.8,
            ),
        ],
    )

    expr = EvaluationMetricExpr(
        evaluation_run_name=run.name,
        metric_name="miou",
        operator=OrdinalComparisonOperator.LT,
        value=0.3,
    )
    match = query_translation.to_match_expression(expr)
    results = DatasetQuery(dataset=dataset, session=db_session).match(match).to_list()

    assert [result.sample_id for result in results] == [image_a.sample_id]


@pytest.mark.parametrize(
    "expr",
    [
        ClassificationMatchExpr(
            subexpr=EvaluationMetricExpr(
                evaluation_run_name="run1",
                metric_name="score",
                operator=OrdinalComparisonOperator.GT,
                value=0.5,
            )
        ),
        ObjectDetectionMatchExpr(
            subexpr=EvaluationMetricExpr(
                evaluation_run_name="run1",
                metric_name="score",
                operator=OrdinalComparisonOperator.GT,
                value=0.5,
            )
        ),
        SegmentationMaskMatchExpr(
            subexpr=EvaluationMetricExpr(
                evaluation_run_name="run1",
                metric_name="score",
                operator=OrdinalComparisonOperator.GT,
                value=0.5,
            )
        ),
    ],
)
def test_to_match_expression__evaluation_metric_inside_annotation_match_rejected(
    expr: ClassificationMatchExpr | ObjectDetectionMatchExpr | SegmentationMaskMatchExpr,
) -> None:
    with pytest.raises(QueryExprError, match="sample-query level"):
        query_translation.to_match_expression(expr)


def test_to_match_expression__evaluation_metric_inside_nested_annotation_match_rejected() -> None:
    expr = ObjectDetectionMatchExpr(
        subexpr=AndExpr(
            children=[
                EvaluationMetricExpr(
                    evaluation_run_name="run1",
                    metric_name="score",
                    operator=OrdinalComparisonOperator.GT,
                    value=0.5,
                )
            ]
        )
    )

    with pytest.raises(QueryExprError, match="sample-query level"):
        query_translation.to_match_expression(expr)
