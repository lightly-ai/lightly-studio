"""Classes for filtering samples by persisted evaluation metrics."""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import ColumnElement, exists
from sqlmodel import col, select

from lightly_studio.core.dataset_query.field_expression import OrdinalOperator
from lightly_studio.core.dataset_query.match_expression import MatchExpression
from lightly_studio.models.evaluation_run import EvaluationRunTable
from lightly_studio.models.evaluation_sample_metric import EvaluationSampleMetricTable
from lightly_studio.models.sample import SampleTable


class EvaluationMetricField:  # noqa: PLW1641
    """Queryable per-sample metric field from an evaluation run.

    Example:
        ``SampleEvaluationQuery.match("run1", EvaluationMetricField("miou") < 0.3)``
    """

    def __init__(self, metric_name: str) -> None:
        """Initialize a queryable metric reference."""
        self.metric_name = metric_name

    def _expression(self, other: float | int, operator: OrdinalOperator) -> MatchExpression:
        return EvaluationMetricMatchExpression(
            metric_name=self.metric_name,
            operator=operator,
            value=other,
        )

    def __gt__(self, other: float | int) -> MatchExpression:
        """Create a greater-than filter."""
        return self._expression(other=other, operator=">")

    def __lt__(self, other: float | int) -> MatchExpression:
        """Create a less-than filter."""
        return self._expression(other=other, operator="<")

    def __ge__(self, other: float | int) -> MatchExpression:
        """Create a greater-than-or-equal filter."""
        return self._expression(other=other, operator=">=")

    def __le__(self, other: float | int) -> MatchExpression:
        """Create a less-than-or-equal filter."""
        return self._expression(other=other, operator="<=")

    def __eq__(self, other: float | int) -> MatchExpression:  # type: ignore[override]
        """Create an equality filter."""
        return self._expression(other=other, operator="==")

    def __ne__(self, other: float | int) -> MatchExpression:  # type: ignore[override]
        """Create an inequality filter."""
        return self._expression(other=other, operator="!=")


@dataclass
class EvaluationMetricMatchExpression(MatchExpression):
    """Correlated EXISTS filter against evaluation sample metrics."""

    metric_name: str
    operator: OrdinalOperator
    value: float | int

    def get(self) -> ColumnElement[bool]:
        """Build a correlated EXISTS clause for the metric comparison."""
        metric_value = col(EvaluationSampleMetricTable.value)
        operations: dict[OrdinalOperator, ColumnElement[bool]] = {
            "<": metric_value < self.value,
            "<=": metric_value <= self.value,
            ">": metric_value > self.value,
            ">=": metric_value >= self.value,
            "==": metric_value == self.value,
            "!=": metric_value != self.value,
        }
        return exists(
            select(1)
            .select_from(EvaluationSampleMetricTable)
            .where(col(EvaluationSampleMetricTable.evaluation_run_id) == col(EvaluationRunTable.id))
            .where(col(EvaluationSampleMetricTable.sample_id) == col(SampleTable.sample_id))
            .where(col(EvaluationSampleMetricTable.metric_name) == self.metric_name)
            .where(operations[self.operator])
            .correlate(EvaluationRunTable, SampleTable)
        )
