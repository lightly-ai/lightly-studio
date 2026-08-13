"""Translate an annotation sort expression into an order by expression."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy import ColumnElement
from sqlalchemy.orm import Mapped
from sqlmodel import Session

from lightly_studio.core.dataset_query.order_by import OrderByAnnotationEvaluationMetricField
from lightly_studio.models.annotation_sort import AnnotationEvaluationMetricSortExpr
from lightly_studio.models.evaluation_annotation_metric import EvaluationAnnotationSide
from lightly_studio.models.evaluation_run import EvaluationRunTable
from lightly_studio.resolvers import evaluation_run_resolver


def sort_expr_to_order_by(
    session: Session,
    annotation_collection_id: UUID,
    sort_expr: AnnotationEvaluationMetricSortExpr,
    annotation_id_column: ColumnElement[Any] | Mapped[Any],
) -> OrderByAnnotationEvaluationMetricField:
    """Translate an annotation sort expression to an order by expression.

    Args:
        session: Database session.
        annotation_collection_id: The browsed annotation source.
        sort_expr: The sort expression from the API request.
        annotation_id_column: Column holding the annotation's sample ID in the query the
            ordering is applied to.

    Returns:
        An order by expression ready to be applied to an annotation query.

    Raises:
        ValueError: If the named evaluation run does not exist, or if the browsed
            annotation source is neither side of the run's pairing.
    """
    run = evaluation_run_resolver.get_by_id(
        session=session, evaluation_id=sort_expr.evaluation_run_id
    )
    if run is None:
        raise ValueError(f"Evaluation run with ID {sort_expr.evaluation_run_id} not found.")

    side = resolve_side(run=run, annotation_collection_id=annotation_collection_id)
    if side is None:
        raise ValueError(
            f"Evaluation run {run.id} involves neither side of annotation source "
            f"{annotation_collection_id}."
        )

    order_by = OrderByAnnotationEvaluationMetricField(
        evaluation_run_id=run.id,
        metric_name=sort_expr.metric_name,
        side=side,
        annotation_id_column=annotation_id_column,
    )
    if sort_expr.direction == "desc":
        order_by.desc()
    return order_by


def resolve_side(
    run: EvaluationRunTable,
    annotation_collection_id: UUID,
) -> EvaluationAnnotationSide | None:
    """Resolve which side of the run's pairing an annotation source is.

    Args:
        run: The evaluation run.
        annotation_collection_id: The browsed annotation source.

    Returns:
        The matching side, or None if the source is neither side of the pairing.
    """
    if annotation_collection_id == run.gt_annotation_collection_id:
        return EvaluationAnnotationSide.GROUND_TRUTH
    if annotation_collection_id == run.pred_annotation_collection_id:
        return EvaluationAnnotationSide.PREDICTION
    return None
