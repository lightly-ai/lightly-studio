"""API routes for dataset videos."""

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Path
from typing_extensions import Annotated

from lightly_studio.api.routes.api.status import HTTP_STATUS_NOT_FOUND
from lightly_studio.api.routes.api.validators import Paginated, PaginatedWithCursor
from lightly_studio.db_manager import SessionDep
from lightly_studio.models.sample import SampleView
from lightly_studio.models.video import FrameView, VideoTable, VideoView, VideoViewsWithCount
from lightly_studio.resolvers import video_resolver
from lightly_studio.resolvers.video_resolver import VideosWithCount

video_router = APIRouter(prefix="/datasets/{dataset_id}/video", tags=["video"])


def _video_table_to_view(video: VideoTable, include_frames: bool = False) -> VideoView:
    """Convert VideoTable to VideoView with proper relationship loading.
    
    Note: We pass video.sample directly and let SQLModel/Pydantic handle
    the conversion to SampleView, similar to how images work.
    
    Args:
        video: The VideoTable instance to convert
        include_frames: Whether to include frames (only for single video view)
    """
    frames = []
    if include_frames:
        # Only load frames if explicitly requested (for single video view)
        # For list view, frames are not needed and would cause N+1 queries
        try:
            # Check if frames are loaded by accessing the relationship
            # This will trigger lazy loading if not already loaded
            if video.frames:
                frames = [
                    FrameView(
                        frame_number=frame.frame_number,
                        frame_timestamp_s=frame.frame_timestamp_s,
                        sample_id=frame.sample_id,
                        sample=frame.sample,  # Let SQLModel handle conversion
                    )
                    for frame in video.frames
                ]
        except Exception:
            # If frames aren't loaded and can't be loaded, just use empty list
            frames = []
    
    return VideoView(
        width=video.width,
        height=video.height,
        duration_s=video.duration_s,
        fps=video.fps,
        file_name=video.file_name,
        file_path_abs=video.file_path_abs,
        sample_id=video.sample_id,
        sample=video.sample,  # Let SQLModel handle conversion to SampleView
        frames=frames,
    )


@video_router.get("/", response_model=VideoViewsWithCount)
def get_all_videos(
    session: SessionDep,
    dataset_id: Annotated[UUID, Path(title="Dataset Id")],
    pagination: Annotated[PaginatedWithCursor, Depends()],
) -> VideoViewsWithCount:
    """Retrieve a list of all videos for a given dataset ID with pagination.

    Args:
        session: The database session.
        dataset_id: The ID of the dataset to retrieve videos for.
        pagination: Pagination parameters including offset and limit.

    Returns:
        A list of videos along with the total count.
    """
    result = video_resolver.get_all_by_dataset_id(
        session=session,
        dataset_id=dataset_id,
        pagination=Paginated(offset=pagination.offset, limit=pagination.limit),
    )
    # Convert VideoTable to VideoView to avoid N+1 queries and ensure proper serialization
    # Don't include frames for list view to avoid performance issues
    # Access all relationships while session is still open to ensure they're loaded
    video_views = []
    for video in result.samples:
        # Ensure sample and its relationships are accessed while session is open
        # This prevents lazy loading during serialization
        sample = video.sample
        _ = sample.tags  # Access tags
        _ = sample.metadata_dict  # Access metadata
        _ = sample.captions  # Access captions
        video_views.append(_video_table_to_view(video, include_frames=False))
    
    return VideoViewsWithCount(
        samples=video_views,
        total_count=result.total_count,
        next_cursor=result.next_cursor,
    )


@video_router.get("/{sample_id}", response_model=VideoView)
def get_video_by_id(
    session: SessionDep,
    sample_id: Annotated[UUID, Path(title="Sample ID")],
) -> VideoView:
    """Retrieve a video for a given dataset ID by its ID.

    Args:
        session: The database session.
        sample_id: The ID of the video to retrieve.

    Returns:
        A video object.
    """
    # Eagerly load frames for single video view to avoid lazy loading
    video = video_resolver.get_by_id(session=session, sample_id=sample_id, include_frames=True)
    if not video:
        raise HTTPException(
            status_code=HTTP_STATUS_NOT_FOUND, detail=f"Video not found: {sample_id}"
        )
    # Access all relationships while session is still open to ensure they're loaded
    sample = video.sample
    _ = sample.tags  # Access tags
    _ = sample.metadata_dict  # Access metadata
    _ = sample.captions  # Access captions
    # Access frames to ensure they're loaded (they should be eagerly loaded now)
    _ = video.frames
    # Access frame samples to ensure they're loaded
    for frame in video.frames:
        _ = frame.sample
        _ = frame.sample.tags
        _ = frame.sample.metadata_dict
        _ = frame.sample.captions
    # Include frames for single video view
    return _video_table_to_view(video, include_frames=True)
