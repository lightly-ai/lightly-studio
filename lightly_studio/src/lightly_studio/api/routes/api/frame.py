"""API routes for dataset frames."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Path
from pydantic import BaseModel, Field
from typing_extensions import Annotated

from lightly_studio.api.routes.api.validators import Paginated, PaginatedWithCursor
from lightly_studio.db_manager import SessionDep
from lightly_studio.models.annotation.annotation_base import AnnotationBaseTable, AnnotationView
from lightly_studio.models.annotation.instance_segmentation import (
    InstanceSegmentationAnnotationView,
)
from lightly_studio.models.annotation.object_detection import ObjectDetectionAnnotationView
from lightly_studio.models.annotation.semantic_segmentation import (
    SemanticSegmentationAnnotationView,
)
from lightly_studio.models.sample import SampleTable, SampleView
from lightly_studio.models.video import (
    FrameView,
    VideoFrameTable,
    VideoFrameView,
    VideoFrameViewsWithCount,
    VideoTable,
    VideoView,
)
from lightly_studio.resolvers import video_frame_resolver
from lightly_studio.resolvers.video_frame_resolver.video_frame_filter import (
    VideoFrameFilter,
)

frame_router = APIRouter(prefix="/datasets/{video_frame_dataset_id}/frame", tags=["frame"])


class ReadVideoFramesRequest(BaseModel):
    """Request body for reading videos."""

    filter: VideoFrameFilter | None = Field(None, description="Filter parameters for video frames")


@frame_router.post("/", response_model=VideoFrameViewsWithCount)
def get_all_frames(
    video_frame_dataset_id: Annotated[UUID, Path(title="Video dataset Id")],
    session: SessionDep,
    pagination: Annotated[PaginatedWithCursor, Depends()],
    body: ReadVideoFramesRequest,
) -> VideoFrameViewsWithCount:
    """Retrieve a list of all frames for a given dataset ID with pagination.

    Args:
        session: The database session.
        video_frame_dataset_id: The ID of the dataset to retrieve frames for.
        pagination: Pagination parameters including offset and limit.
        body: The body containing the filters
    Returns:
        A list of frames along with the total count.
    """
    result = video_frame_resolver.get_all_by_dataset_id(
        session=session,
        dataset_id=video_frame_dataset_id,
        pagination=Paginated(offset=pagination.offset, limit=pagination.limit),
        video_frame_filter=body.filter,
    )

    return VideoFrameViewsWithCount(
        samples=[_build_video_frame_view(vf=frame) for frame in result.samples],
        total_count=result.total_count,
        next_cursor=result.next_cursor,
    )


@frame_router.get("/{sample_id}", response_model=VideoFrameView)
def get_frame_by_id(
    session: SessionDep,
    sample_id: Annotated[UUID, Path(title="Sample Id")],
) -> VideoFrameView:
    """Retrieve a frame by its sample ID within a given dataset.

    Args:
        session: The database session.
        sample_id: The ID of the sample to retrieve.

    Returns:
        A frame corresponding to the given sample ID.
    """
    result = video_frame_resolver.get_by_id(session=session, sample_id=sample_id)

    return _build_video_frame_view(result)


# TODO (Leonardo 11/25): These manual conversions are needed because
# of the circular import between Annotation and Sample.
def _build_annotation_view(a: AnnotationBaseTable) -> AnnotationView:
    return AnnotationView(
        parent_sample_id=a.parent_sample_id,
        dataset_id=a.dataset_id,
        sample_id=a.sample_id,
        annotation_type=a.annotation_type,
        confidence=a.confidence,
        created_at=a.created_at,
        annotation_label=AnnotationView.AnnotationLabel(
            annotation_label_name=a.annotation_label.annotation_label_name
        ),
        object_detection_details=(
            ObjectDetectionAnnotationView(
                x=a.object_detection_details.x,
                y=a.object_detection_details.y,
                width=a.object_detection_details.width,
                height=a.object_detection_details.height,
            )
            if a.object_detection_details
            else None
        ),
        instance_segmentation_details=(
            InstanceSegmentationAnnotationView(
                width=a.instance_segmentation_details.width,
                height=a.instance_segmentation_details.height,
                x=a.instance_segmentation_details.x,
                y=a.instance_segmentation_details.y,
            )
            if a.instance_segmentation_details
            else None
        ),
        semantic_segmentation_details=(
            SemanticSegmentationAnnotationView(
                segmentation_mask=a.semantic_segmentation_details.segmentation_mask,
            )
            if a.semantic_segmentation_details
            else None
        ),
        tags=[AnnotationView.AnnotationViewTag(tag_id=t.tag_id, name=t.name) for t in a.tags],
    )


def _build_sample_view(sample: SampleTable) -> SampleView:
    return SampleView(
        dataset_id=sample.dataset_id,
        sample_id=sample.sample_id,
        created_at=sample.created_at,
        updated_at=sample.updated_at,
        tags=sample.tags,
        metadata_dict=sample.metadata_dict,
        captions=sample.captions,
        annotations=[_build_annotation_view(a) for a in sample.annotations],
    )


def _build_video_view(video: VideoTable) -> VideoView:
    return VideoView(
        width=video.width,
        height=video.height,
        duration_s=video.duration_s,
        fps=video.fps,
        file_name=video.file_name,
        file_path_abs=video.file_path_abs,
        sample_id=video.sample_id,
        sample=_build_sample_view(video.sample),
    )


def _build_video_frame_view(vf: VideoFrameTable) -> VideoFrameView:
    return VideoFrameView(
        frame_number=vf.frame_number,
        frame_timestamp_s=vf.frame_timestamp_s,
        sample_id=vf.sample_id,
        video=_build_video_view(vf.video),
        sample=_build_sample_view(vf.sample),
    )


def build_frame_view(vf: VideoFrameTable) -> FrameView:
    """Create a FrameView."""
    return FrameView(
        frame_number=vf.frame_number,
        frame_timestamp_s=vf.frame_timestamp_s,
        sample_id=vf.sample_id,
        sample=_build_sample_view(vf.sample),
    )
