"""Route to list per-annotation evaluation matches (TP/FP/FN) with crops."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, HTTPException, Path
from pydantic import BaseModel, Field

from lightly_studio.api.routes.api.status import (
    HTTP_STATUS_NOT_FOUND,
    HTTP_STATUS_NOT_IMPLEMENTED,
)
from lightly_studio.api.routes.api.validators import Paginated
from lightly_studio.database.db_manager import SessionDep
from lightly_studio.models.evaluation_annotation_metric import (
    EvaluationMatchesWithCountView,
    EvaluationMatchSortField,
    EvaluationMatchType,
)
from lightly_studio.models.evaluation_confusion_matrix import ConfusionCell
from lightly_studio.models.evaluation_run import EvaluationTaskType
from lightly_studio.models.sort_direction import SortDirection
from lightly_studio.resolvers import (
    evaluation_annotation_metric_resolver,
    evaluation_run_resolver,
)
from lightly_studio.resolvers.image_filter import ImageFilter

get_matches_router = APIRouter()


class GetEvaluationMatchesRequest(BaseModel):
    """Request body for listing evaluation matches."""

    collection_id: UUID = Field(
        ...,
        description="Image collection used to scope the image-level filters.",
    )
    match_types: list[EvaluationMatchType] | None = Field(
        None,
        description="Subset of match types (tp/fp/fn) to keep. None keeps all.",
    )
    annotation_label_ids: list[UUID] | None = Field(
        None,
        description="Keep matches whose ground-truth OR prediction label is in this set.",
    )
    confusion_cell: ConfusionCell | None = Field(
        None,
        description="Confusion-matrix cell (gt_label/pred_label pairing) to filter "
        "matches to. A null label selects the false-positive (no ground truth) or "
        "false-negative (no prediction) margin bucket.",
    )
    image_filter: ImageFilter | None = Field(
        None,
        description="Image-level filter (tags, metadata, dimensions, sample ids).",
    )
    sort_field: EvaluationMatchSortField = Field(
        EvaluationMatchSortField.IOU,
        description="Primary ordering: by IoU (default) or by prediction confidence.",
    )
    sort_direction: SortDirection = Field(
        SortDirection.desc,
        description="Direction applied to the chosen sort field.",
    )
    pagination: Paginated = Field(default_factory=Paginated)


@get_matches_router.post(
    "/evaluation/runs/{evaluation_run_id}/matches",
    response_model=EvaluationMatchesWithCountView,
)
def list_evaluation_matches(
    session: SessionDep,
    dataset_id: Annotated[UUID, Path(title="Dataset ID")],  # noqa: ARG001
    evaluation_run_id: Annotated[UUID, Path(title="Evaluation Run ID")],
    body: GetEvaluationMatchesRequest,
) -> EvaluationMatchesWithCountView:
    """List the per-annotation matches (TP/FP/FN) for an evaluation run.

    Args:
        session: The database session.
        dataset_id: The dataset's UUID (path scoping only).
        evaluation_run_id: The evaluation run whose pairings are listed.
        body: Filter, ordering scope, and pagination parameters.

    Returns:
        Paginated matches enriched with their boxes and parent-image crop.

    Raises:
        HTTPException: 404 if the evaluation run was not found.
        HTTPException: 501 if the run's task type has no per-box pairings.
    """
    run = evaluation_run_resolver.get_by_id(
        session=session,
        evaluation_id=evaluation_run_id,
    )
    if run is None:
        raise HTTPException(
            status_code=HTTP_STATUS_NOT_FOUND,
            detail=f"Evaluation run {evaluation_run_id} not found.",
        )
    if run.task_type != EvaluationTaskType.OBJECT_DETECTION:
        raise HTTPException(
            status_code=HTTP_STATUS_NOT_IMPLEMENTED,
            detail=(
                "Per-box evaluation matches are only available for object detection runs, "
                f"not '{run.task_type.value}'."
            ),
        )
    return evaluation_annotation_metric_resolver.get_matches_with_payload(
        session=session,
        evaluation_run_id=evaluation_run_id,
        collection_id=body.collection_id,
        match_types=body.match_types,
        annotation_label_ids=body.annotation_label_ids,
        confusion_cell=body.confusion_cell,
        image_filter=body.image_filter,
        sort_field=body.sort_field,
        sort_direction=body.sort_direction,
        pagination=body.pagination,
    )
