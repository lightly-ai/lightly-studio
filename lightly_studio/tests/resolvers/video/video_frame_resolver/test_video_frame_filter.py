"""Tests for VideoFrameFilter."""

from __future__ import annotations

from sqlmodel import Session, col, select

from lightly_studio.models.collection import SampleType
from lightly_studio.models.video import VideoFrameTable
from lightly_studio.resolvers.annotations.annotations_filter import AnnotationsFilter
from lightly_studio.resolvers.video_frame_resolver.video_frame_filter import VideoFrameFilter
from tests.helpers_resolvers import (
    AnnotationDetails,
    create_annotation_label,
    create_annotations,
    create_collection,
)
from tests.resolvers.video.helpers import VideoStub, create_video_with_frames


def test_query__annotation_filter(db_session: Session) -> None:
    collection = create_collection(session=db_session, sample_type=SampleType.VIDEO)
    video_frames = create_video_with_frames(
        session=db_session,
        collection_id=collection.collection_id,
        video=VideoStub(path="/videos/a.mp4", fps=1, duration_s=3.0),
    )

    dog_label = create_annotation_label(
        session=db_session,
        dataset_id=video_frames.video_frames_collection_id,
        label_name="dog",
    )
    cat_label = create_annotation_label(
        session=db_session,
        dataset_id=video_frames.video_frames_collection_id,
        label_name="cat",
    )
    create_annotations(
        session=db_session,
        collection_id=video_frames.video_frames_collection_id,
        annotations=[
            AnnotationDetails(
                sample_id=video_frames.frame_sample_ids[0],
                annotation_label_id=dog_label.annotation_label_id,
            ),
            AnnotationDetails(
                sample_id=video_frames.frame_sample_ids[1],
                annotation_label_id=cat_label.annotation_label_id,
            ),
        ],
    )

    query = (
        select(VideoFrameTable)
        .join(VideoFrameTable.sample)
        .order_by(col(VideoFrameTable.frame_number).asc())
    )
    video_frame_filter = VideoFrameFilter(
        annotation_filter=AnnotationsFilter(
            annotation_label_ids=[dog_label.annotation_label_id],
        )
    )

    filtered_query = video_frame_filter.apply(query=query)
    result = db_session.exec(filtered_query).all()
    assert len(result) == 1
    assert result[0].sample_id == video_frames.frame_sample_ids[0]
