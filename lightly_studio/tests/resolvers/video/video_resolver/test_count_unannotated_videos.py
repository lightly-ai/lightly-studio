from __future__ import annotations

from sqlmodel import Session

from lightly_studio.models.annotation.annotation_base import AnnotationType
from lightly_studio.models.collection import SampleType
from lightly_studio.models.unannotated_sample_count import UnannotatedSampleCount
from lightly_studio.resolvers import video_resolver
from lightly_studio.resolvers.annotations.annotations_filter import AnnotationsFilter
from lightly_studio.resolvers.sample_resolver.sample_filter import SampleFilter
from lightly_studio.resolvers.video_resolver.video_filter import VideoFilter
from tests.helpers_resolvers import (
    AnnotationDetails,
    create_annotation_label,
    create_annotations,
    create_collection,
)
from tests.resolvers.video.helpers import VideoStub, create_video_with_frames


def test_count_unannotated_videos(db_session: Session) -> None:
    collection = create_collection(session=db_session, sample_type=SampleType.VIDEO)
    videos = [
        create_video_with_frames(
            session=db_session,
            collection_id=collection.collection_id,
            video=VideoStub(path=path, duration_s=1.0, fps=2.0),
        )
        for path in [
            "frame_car.mp4",
            "direct_running.mp4",
            "unannotated_1.mp4",
            "unannotated_2.mp4",
        ]
    ]
    car_label = create_annotation_label(
        session=db_session,
        root_collection_id=videos[0].video_frames_collection_id,
        label_name="car",
    )
    running_label = create_annotation_label(
        session=db_session, root_collection_id=collection.collection_id, label_name="running"
    )
    create_annotations(
        session=db_session,
        collection_id=videos[0].video_frames_collection_id,
        annotations=[
            AnnotationDetails(
                sample_id=videos[0].frame_sample_ids[0],
                annotation_label_id=car_label.annotation_label_id,
            )
        ],
    )
    create_annotations(
        session=db_session,
        collection_id=collection.collection_id,
        annotations=[
            AnnotationDetails(
                sample_id=videos[1].video_sample_id,
                annotation_label_id=running_label.annotation_label_id,
                annotation_type=AnnotationType.CLASSIFICATION,
            )
        ],
    )

    count = video_resolver.count_unannotated_videos(
        session=db_session,
        collection_id=collection.collection_id,
        video_filter=VideoFilter(
            sample_filter=SampleFilter(
                sample_ids=[videos[0].video_sample_id, videos[2].video_sample_id]
            )
        ),
    )

    assert count == UnannotatedSampleCount(current_count=1, total_count=2)


def test_count_unannotated_videos__source_only_filter(db_session: Session) -> None:
    collection = create_collection(session=db_session, sample_type=SampleType.VIDEO)
    videos = [
        create_video_with_frames(
            session=db_session,
            collection_id=collection.collection_id,
            video=VideoStub(path=path, duration_s=1.0, fps=2.0),
        )
        for path in ["frame_car.mp4", "unannotated.mp4"]
    ]
    car_label = create_annotation_label(
        session=db_session,
        root_collection_id=videos[0].video_frames_collection_id,
        label_name="car",
    )
    annotations = create_annotations(
        session=db_session,
        collection_id=videos[0].video_frames_collection_id,
        annotations=[
            AnnotationDetails(
                sample_id=videos[0].frame_sample_ids[0],
                annotation_label_id=car_label.annotation_label_id,
            )
        ],
    )

    count = video_resolver.count_unannotated_videos(
        session=db_session,
        collection_id=collection.collection_id,
        video_filter=VideoFilter(
            frame_annotation_filter=AnnotationsFilter(
                collection_ids=[annotations[0].annotation_collection_id]
            )
        ),
    )

    assert count == UnannotatedSampleCount(current_count=1, total_count=1)
