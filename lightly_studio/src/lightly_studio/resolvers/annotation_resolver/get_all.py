"""Handler for database operations related to annotations."""

from __future__ import annotations

from collections.abc import Sequence

from pydantic import BaseModel
from sqlmodel import Session, col, func, select

from lightly_studio.api.routes.api.validators import Paginated
from lightly_studio.models.annotation.annotation_base import (
    AnnotationBaseTable,
)
from lightly_studio.models.image import ImageTable
from lightly_studio.models.video import VideoFrameTable, VideoTable
from lightly_studio.resolvers.annotations.annotations_filter import (
    AnnotationsFilter,
)


class GetAllAnnotationsResult(BaseModel):
    """Result of getting all annotations."""

    annotations: Sequence[AnnotationBaseTable]

    total_count: int

    next_cursor: int | None = None


def get_all(
    session: Session,
    pagination: Paginated | None = None,
    filters: AnnotationsFilter | None = None,
) -> GetAllAnnotationsResult:
    """Get all annotations from the database.

    Args:
        session: Database session
        pagination: Optional pagination parameters
        filters: Optional filters to apply to the query

    Returns:
        List of annotations matching the filters
    """
    annotations_statement = select(AnnotationBaseTable)
    annotations_statement = (
        annotations_statement.outerjoin(
            ImageTable, col(ImageTable.sample_id) == col(AnnotationBaseTable.parent_sample_id)
        )
        .outerjoin(
            VideoFrameTable,
            col(VideoFrameTable.sample_id) == col(AnnotationBaseTable.parent_sample_id),
        )
        .outerjoin(VideoTable, col(VideoTable.sample_id) == col(VideoFrameTable.parent_sample_id))
        .order_by(
            func.coalesce(ImageTable.file_path_abs, VideoTable.file_path_abs, "").asc(),
            col(AnnotationBaseTable.created_at).asc(),
            col(AnnotationBaseTable.sample_id).asc(),
        )
    )
    total_count_statement = select(func.count()).select_from(AnnotationBaseTable)

    # Apply filters if provided
    if filters is not None:
        annotations_statement = filters.apply(annotations_statement)
        total_count_statement = filters.apply(total_count_statement)

    # Apply pagination if provided
    if pagination is not None:
        annotations_statement = annotations_statement.offset(pagination.offset).limit(
            pagination.limit
        )

    total_count = session.exec(total_count_statement).one()

    next_cursor = None
    if pagination and pagination.offset + pagination.limit < total_count:
        next_cursor = pagination.offset + pagination.limit

    return GetAllAnnotationsResult(
        annotations=session.exec(annotations_statement).all(),
        total_count=total_count,
        next_cursor=next_cursor,
    )
