"""API routes for dataset videos."""

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Path
from typing_extensions import Annotated

from lightly_studio.api.routes.api.validators import Paginated, PaginatedWithCursor
from lightly_studio.db_manager import SessionDep
from lightly_studio.models.video import VideoTable, VideoView, VideoViewsWithCount
from lightly_studio.resolvers.video_resolver import VideosWithCount
from lightly_studio.resolvers.video_resolver import get_all_by_dataset_id
from lightly_studio.resolvers.video_resolver import get_by_id

video_router = APIRouter(prefix="/datasets/{dataset_id}/video", tags=["video"])


@video_router.get("/", response_model=VideoViewsWithCount)
def get_all_videos(
    session: SessionDep,
    dataset_id: Annotated[UUID, Path(title="Dataset Id")],
    pagination: Annotated[PaginatedWithCursor, Depends()],
) -> VideosWithCount:
    """Retrieve a list of all videos for a given dataset ID with pagination.

    Args:
        session: The database session.
        dataset_id: The ID of the dataset to retrieve videos for.
        pagination: Pagination parameters including offset and limit.

    Return:
        A list of videos along with the total count.
    """
    return get_all_by_dataset_id(
        session=session,
        dataset_id=dataset_id,
        pagination=Paginated(offset=pagination.offset, limit=pagination.limit),
    )


@video_router.get("/{sample_id}", response_model=VideoView)
def get_video_by_id(
    session: SessionDep,
    sample_id: Annotated[UUID, Path(title="Sample ID")],
) -> Optional[VideoTable]:
    """Retrieve a video for a given dataset ID by its ID.

    Args:
        session: The database session.
        dataset_id: The ID of the dataset to retrieve videos for.
        sample_id: The ID of the video to retrieve.

    Return:
        A video object.
    """
    return get_by_id(session=session, sample_id=sample_id)
