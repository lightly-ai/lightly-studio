"""API routes for dataset videos."""

from uuid import UUID

from fastapi import APIRouter, Depends, Path
from typing_extensions import Annotated

from lightly_studio.api.routes.api.validators import PaginatedWithCursor
from lightly_studio.db_manager import SessionDep
from lightly_studio.models.video import VideoViewsWithCount
from lightly_studio.resolvers.video_resolver.get_all_by_dataset_id import (
    get_all_by_dataset_id,
)

videos_router = APIRouter(prefix="/datasets/{dataset_id}/videos", tags=["videos"])


@videos_router.get("/", response_model=VideoViewsWithCount)
def get_all_videos(
    session: SessionDep,
    dataset_id: Annotated[UUID, Path(title="Dataset Id")],
    pagination: Annotated[PaginatedWithCursor, Depends()],
) -> VideoViewsWithCount:
    """Retrieve a list of all videos for a given dataset ID with pagination.

    Parameters:
    -----------

    dataset_id : UUID
        The ID of the dataset to retrieve videos for.
    pagination : PaginatedWithCursor
        Pagination parameters including offset and limit.

    Return:
    -------
        A list of videos along with the total count.
    """
    return get_all_by_dataset_id(session=session, dataset_id=dataset_id, pagination=pagination)
