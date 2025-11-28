"""API routes for dataset videos."""

from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Path
from pydantic import BaseModel, Field
from typing_extensions import Annotated

from lightly_studio.api.routes.api.validators import Paginated, PaginatedWithCursor
from lightly_studio.db_manager import SessionDep
from lightly_studio.models.video import VideoFieldsBoundsView, VideoView, VideoViewsWithCount
from lightly_studio.resolvers import video_resolver
from lightly_studio.resolvers.video_resolver.video_filter import VideoFilter

video_router = APIRouter(prefix="/datasets/{dataset_id}/video", tags=["video"])


class VideoFieldsBoundsBody(BaseModel):
    """The body to retrieve the fields bounds."""

    annotations_frames_labels_id: Optional[List[UUID]] = None


class ReadVideosRequest(BaseModel):
    """Request body for reading videos."""

    filter: Optional[VideoFilter] = Field(None, description="Filter parameters for videos")


@video_router.post("/", response_model=VideoViewsWithCount)
def get_all_videos(
    session: SessionDep,
    dataset_id: Annotated[UUID, Path(title="Dataset Id")],
    pagination: Annotated[PaginatedWithCursor, Depends()],
    body: ReadVideosRequest,
) -> VideoViewsWithCount:
    """Retrieve a list of all videos for a given dataset ID with pagination.

    Args:
        session: The database session.
        dataset_id: The ID of the dataset to retrieve videos for.
        pagination: Pagination parameters including offset and limit.
        body: The body containing filters.

    Returns:
        A list of videos along with the total count.
    """
    return video_resolver.get_all_by_dataset_id(
        session=session,
        dataset_id=dataset_id,
        pagination=Paginated(offset=pagination.offset, limit=pagination.limit),
        filters=body.filter,
    )


@video_router.get("/{sample_id}", response_model=VideoView)
def get_video_by_id(
    session: SessionDep,
    sample_id: Annotated[UUID, Path(title="Sample ID")],
) -> Optional[VideoView]:
    """Retrieve a video for a given dataset ID by its ID.

    Args:
        session: The database session.
        sample_id: The ID of the video to retrieve.

    Returns:
        A video object.
    """
    return video_resolver.get_by_id(session=session, sample_id=sample_id)


@video_router.post("/bounds", response_model=Optional[VideoFieldsBoundsView])
def get_fiedls_bounds(
    session: SessionDep,
    dataset_id: Annotated[UUID, Path(title="Dataset Id")],
    body: VideoFieldsBoundsBody,
) -> Optional[VideoView]:
    """Retrieve the fields bounds for a given dataset ID by its ID.

    Args:
        session: The database session.
        dataset_id: The ID of the dataset to retrieve videos bounds.
        body: The body containg the filters.

    Returns:
        A video fields bounds object.
    """
    return video_resolver.get_table_fields_bounds(
        dataset_id=dataset_id,
        session=session,
        annotations_frames_labels_id=body.annotations_frames_labels_id,
    )
