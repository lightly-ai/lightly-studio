"""Translate GUI evaluation predicates using the Python query API."""

from typing_extensions import assert_never

from lightly_studio.core.dataset_query.annotation_evaluation_metric_expression import (
    AnnotationEvaluationMetricMatchExpression,
)
from lightly_studio.core.dataset_query.annotation_evaluation_query import AnnotationMetricQuery
from lightly_studio.core.dataset_query.boolean_expression import AND, NOT, OR
from lightly_studio.core.dataset_query.evaluation_metric_expression import (
    EvaluationMetricMatchExpression,
)
from lightly_studio.core.dataset_query.match_expression import MatchExpression
from lightly_studio.core.dataset_query.sample_evaluation_query import SampleEvaluationQuery
from lightly_studio.models.query_expr import (
    ConfusionMatchExpr,
    EvaluationMetricAndExpr,
    EvaluationMetricComparisonExpr,
    EvaluationMetricNotExpr,
    EvaluationMetricOrExpr,
    FalseNegativeMatchExpr,
    FalsePositiveMatchExpr,
    SampleEvaluationMatchExpr,
    SampleEvaluationMetricExpr,
)


def to_match_expression(
    expr: SampleEvaluationMatchExpr
    | ConfusionMatchExpr
    | FalsePositiveMatchExpr
    | FalseNegativeMatchExpr,
) -> MatchExpression:
    """Translate an evaluation wrapper, preserving its run and metric scope."""
    if isinstance(expr, SampleEvaluationMatchExpr):
        return SampleEvaluationQuery(
            expr.run_name, *(_to_sample_metric_expression(expr=c) for c in expr.criteria)
        )
    if isinstance(expr, ConfusionMatchExpr):
        return AnnotationMetricQuery.confusion(
            expr.run_name,
            expr.ground_truth,
            expr.prediction,
            *(
                AnnotationEvaluationMetricMatchExpression(
                    metric_name=c.metric_name, operator=c.operator.value, value=c.value
                )
                for c in expr.criteria
            ),
        )
    if isinstance(expr, FalsePositiveMatchExpr):
        return AnnotationMetricQuery.false_positive(
            run_name=expr.run_name, prediction=expr.prediction
        )
    if isinstance(expr, FalseNegativeMatchExpr):
        return AnnotationMetricQuery.false_negative(
            run_name=expr.run_name, ground_truth=expr.ground_truth
        )
    assert_never(expr)


def _to_sample_metric_expression(expr: SampleEvaluationMetricExpr) -> MatchExpression:
    if isinstance(expr, EvaluationMetricComparisonExpr):
        return EvaluationMetricMatchExpression(
            metric_name=expr.metric_name, operator=expr.operator.value, value=expr.value
        )
    if isinstance(expr, EvaluationMetricAndExpr):
        return AND(*(_to_sample_metric_expression(expr=c) for c in expr.children))
    if isinstance(expr, EvaluationMetricOrExpr):
        return OR(*(_to_sample_metric_expression(expr=c) for c in expr.children))
    if isinstance(expr, EvaluationMetricNotExpr):
        return NOT(_to_sample_metric_expression(expr=expr.child))
    assert_never(expr)
