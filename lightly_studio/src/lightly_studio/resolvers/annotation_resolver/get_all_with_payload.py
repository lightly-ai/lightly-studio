"""Get all annotations with payload resolver."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from pydantic import BaseModel
from sqlalchemy.orm import joinedload, load_only
from sqlmodel import Session, col, func, select
from sqlmodel.sql.expression import Select

from lightly_studio.api.routes.api.validators import Paginated
from lightly_studio.models.annotation.annotation_base import (
    AnnotationBaseTable,
    AnnotationWithPayloadView,
)
from lightly_studio.models.dataset import SampleType
from lightly_studio.models.image import ImageTable
from lightly_studio.models.video import VideoFrameTable, VideoTable
from lightly_studio.resolvers.annotations.annotations_filter import (
    AnnotationsFilter,
)


class AnnotationWithPayloadAndCountResult(BaseModel):
    """Response model for counted annotations with payload."""

    class AnnotationWithPayloadView(BaseModel):
        """Response model for annotation with payload."""

        annotation: AnnotationBaseTable
        payload: ImageTable | VideoFrameTable

    annotations: Sequence[AnnotationWithPayloadView]
    total_count: int
    next_cursor: int | None = None


def get_all_with_payload(
    session: Session,
    sample_type: SampleType,
    pagination: Paginated | None = None,
    filters: AnnotationsFilter | None = None,
) -> AnnotationWithPayloadAndCountResult:
    """Get all annotations with payload from the database.

    Args:
        session: Database session
        sample_type: Sample type to filter by
        pagination: Optional pagination parameters
        filters: Optional filters to apply to the query

    Returns:
        List of annotations matching the filters with payload
    """
    base_query = _build_base_query(sample_type=sample_type)

    if filters:
        base_query = filters.apply(base_query)

    annotations_query = base_query.order_by(
        col(AnnotationBaseTable.created_at).asc(),
        col(AnnotationBaseTable.sample_id).asc(),
    )

    total_count_query = select(func.count()).select_from(base_query.subquery())
    total_count = session.exec(total_count_query).one()

    if pagination is not None:
        annotations_query = annotations_query.offset(pagination.offset).limit(pagination.limit)

    next_cursor = None
    if pagination and pagination.offset + pagination.limit < total_count:
        next_cursor = pagination.offset + pagination.limit

    rows = session.exec(annotations_query).all()

    return AnnotationWithPayloadAndCountResult(
        total_count=total_count,
        next_cursor=next_cursor,
        annotations=[
            {"annotation": annotation, "payload": payload} for annotation, payload in rows
        ],
    )


def _build_base_query(
    sample_type: SampleType,
) -> Select[tuple[AnnotationBaseTable, Any]]:
    if sample_type == SampleType.IMAGE:
        return (
            select(AnnotationBaseTable, ImageTable)
            .join(
                ImageTable,
                col(ImageTable.sample_id) == col(AnnotationBaseTable.parent_sample_id),
            )
            .options(
                load_only(
                    ImageTable.file_path_abs,  # type: ignore[arg-type]
                    ImageTable.sample_id,  # type: ignore[arg-type]
                    ImageTable.height,  # type: ignore[arg-type]
                    ImageTable.width,  # type: ignore[arg-type]
                )
            )
        )

    if sample_type == SampleType.VIDEO_FRAME:
        return (
            select(AnnotationBaseTable, VideoFrameTable)
            .join(
                VideoFrameTable,
                col(VideoFrameTable.sample_id) == col(AnnotationBaseTable.parent_sample_id),
            )
            .join(VideoFrameTable.video)
            .options(
                load_only(VideoFrameTable.sample_id),  # type: ignore[arg-type]
                joinedload(VideoFrameTable.video).load_only(
                    VideoTable.height,  # type: ignore[arg-type]
                    VideoTable.width,  # type: ignore[arg-type]
                    VideoTable.file_path_abs,  # type: ignore[arg-type]
                ),
            )
        )

    raise NotImplementedError(f"Unsupported sample type: {sample_type}")
