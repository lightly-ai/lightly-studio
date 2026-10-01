from __future__ import annotations

from uuid import UUID

import pytest
from sqlmodel import Session

from lightly_studio.models.annotation.annotation_base import AnnotationType
from lightly_studio.models.collection import SampleType
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
from tests.resolvers.video.helpers import VideoStub, create_video, create_video_with_frames


def test_count_video_frame_annotations_by_video_collection_without_filter(
    db_session: Session,
) -> None:
    collection = create_collection(session=db_session, sample_type=SampleType.VIDEO)
    collection_id = collection.collection_id

    # Create videos
    video_frames_data = create_video_with_frames(
        session=db_session,
        collection_id=collection_id,
        video=VideoStub(path="/path/to/sample1.mp4"),
    )

    video_frames_data_1 = create_video_with_frames(
        session=db_session,
        collection_id=collection_id,
        video=VideoStub(path="/path/to/sample2.mp4"),
    )

    video_frames_data_2 = create_video_with_frames(
        session=db_session,
        collection_id=collection_id,
        video=VideoStub(path="/path/to/sample3.mp4"),
    )

    video_frame_id = video_frames_data.frame_sample_ids[0]
    video_frame_id_1 = video_frames_data_1.frame_sample_ids[0]
    video_frame_id_2 = video_frames_data_2.frame_sample_ids[2]

    # Create annotations labels
    car_label = create_annotation_label(
        session=db_session,
        root_collection_id=collection_id,
        label_name="car",
    )

    airplane_label = create_annotation_label(
        session=db_session,
        root_collection_id=collection_id,
        label_name="airplane",
    )

    create_annotation_label(
        session=db_session,
        root_collection_id=collection_id,
        label_name="house",
    )

    create_annotations(
        session=db_session,
        collection_id=collection_id,
        annotations=[
            AnnotationDetails(
                sample_id=video_frame_id,
                annotation_label_id=car_label.annotation_label_id,
            ),
            AnnotationDetails(
                sample_id=video_frame_id_1,
                annotation_label_id=airplane_label.annotation_label_id,
            ),
            AnnotationDetails(
                sample_id=video_frame_id_1,
                annotation_label_id=airplane_label.annotation_label_id,
            ),
            AnnotationDetails(
                sample_id=video_frame_id_2,
                annotation_label_id=airplane_label.annotation_label_id,
            ),
        ],
    )

    annotations = video_resolver.count_video_frame_annotations_by_video_collection(
        session=db_session,
        collection_id=collection_id,
    )

    assert len(annotations) == 2

    assert annotations[0].label_name == "airplane"
    assert annotations[0].total_count == 2
    assert annotations[0].current_count == 2

    assert annotations[1].label_name == "car"
    assert annotations[1].total_count == 1
    assert annotations[1].current_count == 1


def test_count_video_frame_annotations_by_video_collection_with_annotation_filter(
    db_session: Session,
) -> None:
    collection = create_collection(session=db_session, sample_type=SampleType.VIDEO)
    collection_id = collection.collection_id

    # Create videos
    video_frames_data = create_video_with_frames(
        session=db_session,
        collection_id=collection_id,
        video=VideoStub(path="/path/to/sample1.mp4"),
    )

    video_frames_data_1 = create_video_with_frames(
        session=db_session,
        collection_id=collection_id,
        video=VideoStub(path="/path/to/sample2.mp4"),
    )

    video_frames_data_2 = create_video_with_frames(
        session=db_session,
        collection_id=collection_id,
        video=VideoStub(path="/path/to/sample3.mp4"),
    )

    video_frame_id = video_frames_data.frame_sample_ids[0]
    video_frame_id_1 = video_frames_data_1.frame_sample_ids[0]
    video_frame_id_2 = video_frames_data_2.frame_sample_ids[2]

    # Create annotations labels
    car_label = create_annotation_label(
        session=db_session,
        root_collection_id=collection_id,
        label_name="car",
    )

    airplane_label = create_annotation_label(
        session=db_session,
        root_collection_id=collection_id,
        label_name="airplane",
    )

    create_annotation_label(
        session=db_session,
        root_collection_id=collection_id,
        label_name="house",
    )

    create_annotations(
        session=db_session,
        collection_id=collection_id,
        annotations=[
            AnnotationDetails(
                sample_id=video_frame_id,
                annotation_label_id=car_label.annotation_label_id,
            ),
            AnnotationDetails(
                sample_id=video_frame_id_1,
                annotation_label_id=airplane_label.annotation_label_id,
            ),
            AnnotationDetails(
                sample_id=video_frame_id_1,
                annotation_label_id=airplane_label.annotation_label_id,
            ),
            AnnotationDetails(
                sample_id=video_frame_id_2,
                annotation_label_id=airplane_label.annotation_label_id,
            ),
        ],
    )

    annotations = video_resolver.count_video_frame_annotations_by_video_collection(
        session=db_session,
        collection_id=collection_id,
        filters=VideoFilter(
            frame_annotation_filter=AnnotationsFilter(
                annotation_label_ids=[airplane_label.annotation_label_id]
            ),
            sample_filter=SampleFilter(),
        ),
    )

    assert len(annotations) == 2

    assert annotations[0].label_name == "airplane"
    assert annotations[0].total_count == 2
    assert annotations[0].current_count == 2

    assert annotations[1].label_name == "car"
    assert annotations[1].total_count == 1
    assert annotations[1].current_count == 0


def test_count_video_annotations_by_video_collection__direct_video_annotations(
    db_session: Session,
) -> None:
    collection = create_collection(session=db_session, sample_type=SampleType.VIDEO)
    collection_id = collection.collection_id

    # ``video_with_running`` is labelled "Running" both on one of its frames and
    # directly on the video, so it must still be counted only once.
    video_with_running = create_video_with_frames(
        session=db_session,
        collection_id=collection_id,
        video=VideoStub(path="/path/to/running.mp4"),
    )
    video_with_jumping = create_video(
        session=db_session,
        collection_id=collection_id,
        video=VideoStub(path="/path/to/jumping.mp4"),
    )
    create_video(
        session=db_session,
        collection_id=collection_id,
        video=VideoStub(path="/path/to/unlabeled.mp4"),
    )

    running_label = create_annotation_label(
        session=db_session,
        root_collection_id=collection_id,
        label_name="Running",
    )
    jumping_label = create_annotation_label(
        session=db_session,
        root_collection_id=collection_id,
        label_name="Jumping",
    )

    create_annotations(
        session=db_session,
        collection_id=collection_id,
        annotations=[
            AnnotationDetails(
                sample_id=video_with_running.frame_sample_ids[0],
                annotation_label_id=running_label.annotation_label_id,
                annotation_type=AnnotationType.CLASSIFICATION,
            ),
            AnnotationDetails(
                sample_id=video_with_running.video_sample_id,
                annotation_label_id=running_label.annotation_label_id,
                annotation_type=AnnotationType.CLASSIFICATION,
            ),
            AnnotationDetails(
                sample_id=video_with_jumping.sample_id,
                annotation_label_id=jumping_label.annotation_label_id,
                annotation_type=AnnotationType.CLASSIFICATION,
            ),
        ],
    )

    # Without a filter: both labels are counted, and the video labelled via both
    # a frame and a direct annotation is counted once (total_count == 1).
    annotations = video_resolver.count_video_frame_annotations_by_video_collection(
        session=db_session,
        collection_id=collection_id,
    )

    assert len(annotations) == 2
    assert annotations[0].label_name == "Jumping"
    assert annotations[0].total_count == 1
    assert annotations[0].current_count == 1
    assert annotations[1].label_name == "Running"
    assert annotations[1].total_count == 1
    assert annotations[1].current_count == 1

    # With a filter on "Running": totals are unchanged, but only videos matching
    # the filter contribute to current_count.
    filtered_annotations = video_resolver.count_video_frame_annotations_by_video_collection(
        session=db_session,
        collection_id=collection_id,
        filters=VideoFilter(
            frame_annotation_filter=AnnotationsFilter(
                annotation_label_ids=[running_label.annotation_label_id]
            ),
            sample_filter=SampleFilter(),
        ),
    )

    assert len(filtered_annotations) == 2
    assert filtered_annotations[0].label_name == "Jumping"
    assert filtered_annotations[0].total_count == 1
    assert filtered_annotations[0].current_count == 0
    assert filtered_annotations[1].label_name == "Running"
    assert filtered_annotations[1].total_count == 1
    assert filtered_annotations[1].current_count == 1


@pytest.fixture
def typed_collection_id(db_session: Session) -> UUID:
    collection = create_collection(session=db_session, sample_type=SampleType.VIDEO)
    collection_id = collection.collection_id

    video_frames_data = create_video_with_frames(
        session=db_session,
        collection_id=collection_id,
        video=VideoStub(path="/path/to/sample1.mp4"),
    )
    video_frame_id = video_frames_data.frame_sample_ids[0]

    scene_label = create_annotation_label(
        session=db_session,
        root_collection_id=collection_id,
        label_name="scene",
    )
    car_label = create_annotation_label(
        session=db_session,
        root_collection_id=collection_id,
        label_name="car",
    )

    create_annotations(
        session=db_session,
        collection_id=collection_id,
        annotations=[
            AnnotationDetails(
                sample_id=video_frame_id,
                annotation_label_id=scene_label.annotation_label_id,
                annotation_type=AnnotationType.CLASSIFICATION,
            ),
            AnnotationDetails(
                sample_id=video_frame_id,
                annotation_label_id=car_label.annotation_label_id,
                annotation_type=AnnotationType.OBJECT_DETECTION,
            ),
        ],
    )

    return collection_id


@pytest.mark.parametrize(
    ("annotation_type", "expected_counts"),
    [
        (None, {"scene": (1, 1), "car": (1, 1)}),
        (AnnotationType.CLASSIFICATION, {"scene": (1, 1)}),
        (AnnotationType.OBJECT_DETECTION, {"car": (1, 1)}),
    ],
)
def test_count_video_frame_annotations_by_video_collection_filters_by_annotation_type(
    db_session: Session,
    typed_collection_id: UUID,
    annotation_type: AnnotationType | None,
    expected_counts: dict[str, tuple[int, int]],
) -> None:
    annotations = video_resolver.count_video_frame_annotations_by_video_collection(
        session=db_session,
        collection_id=typed_collection_id,
        annotation_type=annotation_type,
    )

    counts = {a.label_name: (a.total_count, a.current_count) for a in annotations}
    assert counts == expected_counts
