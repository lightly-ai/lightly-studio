"""Route to get the per-annotation evaluation metrics available for an annotation source."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Path

from lightly_studio.database.db_manager import SessionDep
from lightly_studio.models.evaluation_annotation_metric import (
    EvaluationRunAnnotationMetricsInfoView,
)
from lightly_studio.resolvers import evaluation_annotation_metric_resolver

get_annotation_metrics_info_router = APIRouter()


@get_annotation_metrics_info_router.get(
    "/evaluation/metrics/annotation/info",
    response_model=list[EvaluationRunAnnotationMetricsInfoView],
)
def get_evaluation_annotation_metrics_info(
    session: SessionDep,
    collection_id: Annotated[UUID, Path(title="collection Id")],
) -> list[EvaluationRunAnnotationMetricsInfoView]:
    """Get the per-annotation metrics of every evaluation run involving an annotation source.

    Populates the annotations grid's sort options, so it lists only what the backend can
    resolve to a side of a run's pairing.

    Args:
        session: The database session.
        collection_id: The browsed annotation source.

    Returns:
        One entry per evaluation run involving the source, each carrying the run ID, name,
        task type and recorded metric names.
    """
    return evaluation_annotation_metric_resolver.get_metrics_info_by_collection_id(
        session=session,
        collection_id=collection_id,
    )
