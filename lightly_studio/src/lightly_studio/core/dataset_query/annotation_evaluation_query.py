"""Classes and functions for building queries against annotation evaluation metrics."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

from sqlalchemy import ColumnElement, exists
from sqlalchemy.orm import aliased
from sqlalchemy.sql.selectable import Select
from sqlmodel import col, select

from lightly_studio.core.dataset_query.annotation_evaluation_metric_expression import (
    AnnotationEvaluationMetricMatchExpression,
)
from lightly_studio.core.dataset_query.match_expression import MatchExpression
from lightly_studio.models.annotation.annotation_base import AnnotationBaseTable
from lightly_studio.models.annotation_label import AnnotationLabelTable
from lightly_studio.models.collection import CollectionTable
from lightly_studio.models.evaluation_annotation_metric import EvaluationAnnotationMetricTable
from lightly_studio.models.evaluation_run import EvaluationRunTable
from lightly_studio.models.sample import SampleTable

# TODO(lukas, 07/2026): More match kinds will be added later.
AnnotationMetricMatchKind = Literal["confusion"]


@dataclass
class AnnotationMetricQuery(MatchExpression):
    """Query samples by annotation-level evaluation results.

    This query matches samples that belong to an evaluation run and contain annotation
    pairs in a selected confusion-matrix cell, optionally constrained by persisted
    annotation metrics.

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

    match_kind: AnnotationMetricMatchKind
    run_name: str
    gt_label_name: str
    pred_label_name: str
    criteria: list[AnnotationEvaluationMetricMatchExpression]

    @classmethod
    def confusion(
        cls,
        run_name: str,
        ground_truth: str,
        prediction: str,
        *criteria: AnnotationEvaluationMetricMatchExpression,
    ) -> AnnotationMetricQuery:
        """Match samples by confusion-matrix cell within an evaluation run.

        Example:
            ```python
            AnnotationMetricQuery.confusion(
                "run1",
                "cat",
                "dog",
                AnnotationEvaluationMetricField("iou") < 0.3,
            )
            ```

        Args:
            run_name: The evaluation run name to match metrics against.
            ground_truth: Ground-truth annotation class name.
            prediction: Predicted annotation class name.
            criteria: Zero or more metric comparisons that must all match the same
                annotation pair.
        """
        return cls(
            match_kind="confusion",
            run_name=run_name,
            gt_label_name=ground_truth,
            pred_label_name=prediction,
            criteria=list(criteria),
        )

    def get(self) -> ColumnElement[bool]:
        """Get the annotation evaluation match expression."""
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
        return exists(subquery.where(self._matching_metric_exists_expression()))

    def _matching_metric_exists_expression(self) -> ColumnElement[bool]:
        if self.match_kind != "confusion":
            raise ValueError(f"Unsupported annotation metric match kind: {self.match_kind}")

        candidate_metric = aliased(EvaluationAnnotationMetricTable)
        metric_subquery = self._build_confusion_metric_subquery(metric_table=candidate_metric)
        for criterion in self.criteria:
            metric_subquery = metric_subquery.where(
                self._matching_metric_criterion_exists_expression(
                    candidate_metric=candidate_metric,
                    criterion=criterion,
                )
            )
        return exists(
            metric_subquery
            # Keep EvaluationRunTable and SampleTable as outer references so metrics are matched
            # against the selected run and current sample.
            .correlate(EvaluationRunTable, SampleTable)
        )

    def _matching_metric_criterion_exists_expression(
        self,
        candidate_metric: Any,
        criterion: AnnotationEvaluationMetricMatchExpression,
    ) -> ColumnElement[bool]:
        return exists(
            select(1)
            .select_from(EvaluationAnnotationMetricTable)
            .where(
                col(EvaluationAnnotationMetricTable.evaluation_run_id)
                == col(candidate_metric.evaluation_run_id)
            )
            .where(
                col(EvaluationAnnotationMetricTable.sample_id) == col(candidate_metric.sample_id)
            )
            .where(
                col(EvaluationAnnotationMetricTable.gt_annotation_id)
                == col(candidate_metric.gt_annotation_id)
            )
            .where(
                col(EvaluationAnnotationMetricTable.pred_annotation_id)
                == col(candidate_metric.pred_annotation_id)
            )
            .where(criterion.get())
            .correlate(candidate_metric)
        )

    def _build_confusion_metric_subquery(
        self,
        metric_table: Any = EvaluationAnnotationMetricTable,
    ) -> Select[tuple[int]]:
        # TODO(lukas, 07/2026): This method is close to
        # _build_confusion_cell_subquery() from SampleFilter, consider joining/sharing code.
        gt_annotation = aliased(AnnotationBaseTable)
        pred_annotation = aliased(AnnotationBaseTable)
        gt_label = aliased(AnnotationLabelTable)
        pred_label = aliased(AnnotationLabelTable)

        # The joins act as recursive field accessors, e.g. to access
        # `EvaluationAnnotationMetricTable.gt_annotation.annotation_label.name`, we need to join
        # three tables. And note that EvaluationAnnotationMetricTable only has the
        # `gt_annotation_id` field, which acts as a reference to ground truth annotation.
        return (
            select(1)
            .select_from(metric_table)
            .join(
                gt_annotation,
                col(metric_table.gt_annotation_id) == col(gt_annotation.sample_id),
                isouter=True,
            )
            .join(
                pred_annotation,
                col(metric_table.pred_annotation_id) == col(pred_annotation.sample_id),
                isouter=True,
            )
            .join(
                gt_label,
                col(gt_annotation.annotation_label_id) == col(gt_label.annotation_label_id),
                isouter=True,
            )
            .join(
                pred_label,
                col(pred_annotation.annotation_label_id) == col(pred_label.annotation_label_id),
                isouter=True,
            )
            .where(col(metric_table.evaluation_run_id) == col(EvaluationRunTable.id))
            .where(col(metric_table.sample_id) == col(SampleTable.sample_id))
            .where(col(gt_label.annotation_label_name) == self.gt_label_name)
            .where(col(pred_label.annotation_label_name) == self.pred_label_name)
        )
