"""API routes for dataset frames."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Path
from typing_extensions import Annotated

from lightly_studio.api.routes.api.validators import Paginated, PaginatedWithCursor
from lightly_studio.db_manager import SessionDep
from lightly_studio.models.video import VideoFrameViewsWithCount
from lightly_studio.resolvers import (
    video_frame_resolver,
)
from lightly_studio.resolvers.video_frame_resolver.get_all_by_dataset_id import VideoFramesWithCount

frame_router = APIRouter(prefix="/datasets/{video_frame_dataset_id}/frame", tags=["frame"])


@frame_router.get("/", response_model=VideoFrameViewsWithCount)
def get_all_frames(
    video_frame_dataset_id: Annotated[UUID, Path(title="Video frame dataset Id")],
    session: SessionDep,
    pagination: Annotated[PaginatedWithCursor, Depends()],
) -> VideoFramesWithCount:
    """Retrieve a list of all frames for a given dataset ID with pagination.

    Args:
        session: The database session.
        video_frame_dataset_id: The ID of the dataset to retrieve frames for.
        pagination: Pagination parameters including offset and limit.

    Return:
        A list of frames along with the total count.
    """
    return video_frame_resolver.get_all_by_dataset_id(
        session=session,
        dataset_id=video_frame_dataset_id,
        pagination=Paginated(offset=pagination.offset, limit=pagination.limit),
    )
