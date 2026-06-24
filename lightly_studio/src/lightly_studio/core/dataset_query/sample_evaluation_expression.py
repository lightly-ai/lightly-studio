"""Classes and functions for building queries against sample evaluation metrics."""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import ColumnElement, exists
from sqlmodel import col, select

from lightly_studio.core.dataset_query.match_expression import MatchExpression
from lightly_studio.models.collection import CollectionTable
from lightly_studio.models.evaluation_run import EvaluationRunTable
from lightly_studio.models.evaluation_sample_metric import EvaluationSampleMetricTable
from lightly_studio.models.sample import SampleTable


@dataclass
class SampleEvaluationQuery(MatchExpression):
    """Query if a sample has evaluation metrics matching a criterion."""

    run_name: str
    criteria: list[MatchExpression]

    def __init__(self, run_name: str, *criteria: MatchExpression):
        """Combine multiple sample evaluation criteria into a single expression using AND.

        Example:
            ``SampleEvaluationQuery.match("run1", EvaluationMetricField("miou") < 0.3)``

        Args:
            run_name: The evaluation run name to match metrics against.
            criteria: The evaluation metric criteria to combine.

        Returns:
            A single match expression for satisfying all criteria.
        """
        self.run_name = run_name
        self.criteria = list(criteria)

    def get(self) -> ColumnElement[bool]:
        """Get the sample evaluation match expression."""
        sample_dataset_id = (
            select(CollectionTable.dataset_id)
            .where(col(CollectionTable.collection_id) == col(SampleTable.collection_id))
            .correlate(SampleTable)
            .scalar_subquery()
        )
        # Evaluation run names are unique per dataset, so this resolves at most one run
        # for the current sample's dataset.
        subquery = (
            select(1)
            .select_from(EvaluationRunTable)
            .where(col(EvaluationRunTable.dataset_id) == sample_dataset_id)
            .where(col(EvaluationRunTable.name) == self.run_name)
        )
        # A run can cover only a subset of samples. Select only samples evaluated by the run.
        subquery = subquery.where(self._sample_is_part_of_run_expression())
        for criterion in self.criteria:
            # Apply all the evaluation metric criteria, composed out of
            # `EvaluationMetricMatchExpression` instances.
            subquery = subquery.where(criterion.get())
        return exists(subquery)

    def _sample_is_part_of_run_expression(self) -> ColumnElement[bool]:
        return exists(
            select(1)
            .select_from(EvaluationSampleMetricTable)
            .where(col(EvaluationSampleMetricTable.evaluation_run_id) == col(EvaluationRunTable.id))
            .where(col(EvaluationSampleMetricTable.sample_id) == col(SampleTable.sample_id))
            # Keep EvaluationRunTable and SampleTable as outer references so metrics are matched
            # against the selected run and current sample.
            .correlate(EvaluationRunTable, SampleTable)
        )
