from __future__ import annotations

import pytest
from sqlmodel import col, select

from lightly_studio.core.dataset_query.evaluation_metric_expression import EvaluationMetricField
from lightly_studio.core.dataset_query.match_expression import MatchExpression
from lightly_studio.models.evaluation_run import EvaluationRunTable
from lightly_studio.models.evaluation_sample_metric import EvaluationSampleMetricTable


def test_evaluation_metric_field__sql_filters_metric_value() -> None:
    query = (
        select(EvaluationSampleMetricTable)
        .join(
            EvaluationRunTable,
            col(EvaluationSampleMetricTable.evaluation_run_id) == col(EvaluationRunTable.id),
        )
        .where(col(EvaluationRunTable.name) == "run1")
        .where((EvaluationMetricField(metric_name="score") >= 0.5).get())
    )
    sql = str(query.compile(compile_kwargs={"literal_binds": True})).lower()

    assert "from evaluation_sample_metric" in sql
    assert "join evaluation_run" in sql
    assert "evaluation_run.name = 'run1'" in sql
    assert "evaluation_sample_metric.metric_name = 'score'" in sql
    assert "evaluation_sample_metric.value >= 0.5" in sql


@pytest.mark.parametrize(
    ("expression", "expected_sql"),
    [
        (
            EvaluationMetricField(metric_name="score") > 0.5,
            "evaluation_sample_metric.value > 0.5",
        ),
        (
            EvaluationMetricField(metric_name="score") >= 0.5,
            "evaluation_sample_metric.value >= 0.5",
        ),
        (
            EvaluationMetricField(metric_name="score") < 0.5,
            "evaluation_sample_metric.value < 0.5",
        ),
        (
            EvaluationMetricField(metric_name="score") <= 0.5,
            "evaluation_sample_metric.value <= 0.5",
        ),
        (
            EvaluationMetricField(metric_name="score") == 0.5,
            "evaluation_sample_metric.value = 0.5",
        ),
        (
            EvaluationMetricField(metric_name="score") != 0.5,
            "evaluation_sample_metric.value != 0.5",
        ),
    ],
)
def test_evaluation_metric_field__operators(expression: MatchExpression, expected_sql: str) -> None:
    query = select(
        EvaluationSampleMetricTable,
    ).where(expression.get())
    sql = str(query.compile(compile_kwargs={"literal_binds": True})).lower()

    assert expected_sql in sql
