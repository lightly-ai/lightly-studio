from __future__ import annotations

import pytest
from sqlmodel import select

from lightly_studio.core.dataset_query.annotation_evaluation_metric_expression import (
    AnnotationEvaluationMetricField,
)
from lightly_studio.core.dataset_query.match_expression import MatchExpression
from lightly_studio.models.evaluation_annotation_metric import EvaluationAnnotationMetricTable
from lightly_studio.models.evaluation_run import EvaluationRunTable
from lightly_studio.models.sample import SampleTable


def test_annotation_evaluation_metric_field__sql_filters_metric_value() -> None:
    query = select(EvaluationRunTable, SampleTable).where(
        (AnnotationEvaluationMetricField(metric_name="score") >= 0.5).get()
    )
    sql = " ".join(str(query.compile(compile_kwargs={"literal_binds": True})).lower().split())

    assert "evaluation_annotation_metric" in sql.split("where")[0]
    assert "evaluation_annotation_metric.metric_name = 'score'" in sql
    assert "evaluation_annotation_metric.value >= 0.5" in sql
    assert "exists (select 1" not in sql


@pytest.mark.parametrize(
    ("expression", "expected_sql"),
    [
        (
            AnnotationEvaluationMetricField(metric_name="score") > 0.5,
            "evaluation_annotation_metric.value > 0.5",
        ),
        (
            AnnotationEvaluationMetricField(metric_name="score") >= 0.5,
            "evaluation_annotation_metric.value >= 0.5",
        ),
        (
            AnnotationEvaluationMetricField(metric_name="score") < 0.5,
            "evaluation_annotation_metric.value < 0.5",
        ),
        (
            AnnotationEvaluationMetricField(metric_name="score") <= 0.5,
            "evaluation_annotation_metric.value <= 0.5",
        ),
        (
            AnnotationEvaluationMetricField(metric_name="score") == 0.5,
            "evaluation_annotation_metric.value = 0.5",
        ),
        (
            AnnotationEvaluationMetricField(metric_name="score") != 0.5,
            "evaluation_annotation_metric.value != 0.5",
        ),
    ],
)
def test_annotation_evaluation_metric_field__operators(
    expression: MatchExpression, expected_sql: str
) -> None:
    query = select(EvaluationAnnotationMetricTable).where(expression.get())
    sql = str(query.compile(compile_kwargs={"literal_binds": True})).lower()

    assert expected_sql in sql
