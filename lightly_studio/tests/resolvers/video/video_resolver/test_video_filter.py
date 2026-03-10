"""Tests for VideoFilter."""

from __future__ import annotations

from sqlmodel import Session, select

from lightly_studio.models.collection import SampleType
from lightly_studio.models.video import VideoTable
from lightly_studio.resolvers.annotations.annotations_filter import AnnotationsFilter
from lightly_studio.resolvers.video_resolver.video_filter import VideoFilter
from tests.helpers_resolvers import (
    AnnotationDetails,
    create_annotation_label,
    create_annotations,
    create_collection,
)
from tests.resolvers.video.helpers import VideoStub, create_video_with_frames


def test_query__annotation_filter(db_session: Session) -> None:
    collection = create_collection(session=db_session, sample_type=SampleType.VIDEO)
    video_with_annotation = create_video_with_frames(
        session=db_session,
        collection_id=collection.collection_id,
        video=VideoStub(path="with_annotation.mp4"),
    )
    create_video_with_frames(
        session=db_session,
        collection_id=collection.collection_id,
        video=VideoStub(path="without_annotation.mp4"),
    )
    label = create_annotation_label(
        session=db_session,
        dataset_id=video_with_annotation.video_frames_collection_id,
        label_name="car",
    )
    create_annotations(
        session=db_session,
        collection_id=video_with_annotation.video_frames_collection_id,
        annotations=[
            AnnotationDetails(
                sample_id=video_with_annotation.frame_sample_ids[0],
                annotation_label_id=label.annotation_label_id,
            )
        ],
    )

    query = select(VideoTable).join(VideoTable.sample)
    video_filter = VideoFilter(
        annotation_filter=AnnotationsFilter(
            annotation_label_ids=[label.annotation_label_id],
        )
    )

    filtered_query = video_filter.apply(query=query)
    result = db_session.exec(filtered_query).all()
    assert len(result) == 1
    assert result[0].sample_id == video_with_annotation.video_sample_id
