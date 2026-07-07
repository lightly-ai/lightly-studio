"""Classes for filtering samples by persisted annotation evaluation metrics."""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import ColumnElement, and_
from sqlmodel import col

from lightly_studio.core.dataset_query.field_expression import OrdinalOperator
from lightly_studio.core.dataset_query.match_expression import MatchExpression
from lightly_studio.models.evaluation_annotation_metric import EvaluationAnnotationMetricTable


class AnnotationEvaluationMetricField:  # noqa: PLW1641
    """Queryable annotation metric field for annotation-level evaluation results.

    Use this field inside :meth:`AnnotationMetricQuery.confusion` to filter samples by
    persisted annotation metrics such as IoU.

    Example:
        ```python
        AnnotationMetricQuery.confusion(
            "run1",
            "cat",
            "dog",
            AnnotationEvaluationMetricField("iou") > 0.3,
        )
        ```
    """

    def __init__(self, metric_name: str) -> None:
        """Initialize a queryable annotation metric reference."""
        self.metric_name = metric_name

    def _expression(
        self, other: float | int, operator: OrdinalOperator
    ) -> AnnotationEvaluationMetricMatchExpression:
        return AnnotationEvaluationMetricMatchExpression(
            metric_name=self.metric_name,
            operator=operator,
            value=other,
        )

    def __gt__(self, other: float | int) -> AnnotationEvaluationMetricMatchExpression:
        """Create a greater-than filter."""
        return self._expression(other=other, operator=">")

    def __lt__(self, other: float | int) -> AnnotationEvaluationMetricMatchExpression:
        """Create a less-than filter."""
        return self._expression(other=other, operator="<")

    def __ge__(self, other: float | int) -> AnnotationEvaluationMetricMatchExpression:
        """Create a greater-than-or-equal filter."""
        return self._expression(other=other, operator=">=")

    def __le__(self, other: float | int) -> AnnotationEvaluationMetricMatchExpression:
        """Create a less-than-or-equal filter."""
        return self._expression(other=other, operator="<=")

    def __eq__(self, other: float | int) -> AnnotationEvaluationMetricMatchExpression:  # type: ignore[override]
        """Create an equality filter."""
        return self._expression(other=other, operator="==")

    def __ne__(self, other: float | int) -> AnnotationEvaluationMetricMatchExpression:  # type: ignore[override]
        """Create an inequality filter."""
        return self._expression(other=other, operator="!=")


@dataclass
class AnnotationEvaluationMetricMatchExpression(MatchExpression):
    """A match expression that filters samples by their annotation evaluation metrics.

    This expression constructs a SQL query predicate targeting the evaluation annotation
    metrics table. It filters for a specific metric by its name and asserts that the metric's
    numeric value satisfies the specified comparison operator against a given threshold.
    """

    # TODO(lukas 6/2026): Validate that this expression is not nested inside AND/OR/NOT combinators.
    metric_name: str
    operator: OrdinalOperator
    value: float | int

    def get(self) -> ColumnElement[bool]:
        """Build a predicate against the current annotation metric row."""
        metric_value = col(EvaluationAnnotationMetricTable.value)
        operations: dict[OrdinalOperator, ColumnElement[bool]] = {
            "<": metric_value < self.value,
            "<=": metric_value <= self.value,
            ">": metric_value > self.value,
            ">=": metric_value >= self.value,
            "==": metric_value == self.value,
            "!=": metric_value != self.value,
        }
        return and_(
            col(EvaluationAnnotationMetricTable.metric_name) == self.metric_name,
            operations[self.operator],
        )
