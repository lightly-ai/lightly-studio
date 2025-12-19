from sqlmodel import Session

from lightly_studio.models.collection import SampleType
from lightly_studio.resolvers import video_resolver
from lightly_studio.resolvers.video_resolver.video_count_annotations_filter import (
    VideoCountAnnotationsFilter,
)
from tests.helpers_resolvers import create_annotation, create_annotation_label, create_collection
from tests.resolvers.video.helpers import VideoStub, create_video_with_frames


def test_count_video_frame_annotations_by_video_collection_without_filter(
    test_db: Session,
) -> None:
    collection = create_collection(session=test_db, sample_type=SampleType.VIDEO)
    collection_id = collection.collection_id

    # Create videos
    video_frames_data = create_video_with_frames(
        session=test_db,
        collection_id=collection_id,
        video=VideoStub(path="/path/to/sample1.mp4"),
    )

    video_frames_data_1 = create_video_with_frames(
        session=test_db,
        collection_id=collection_id,
        video=VideoStub(path="/path/to/sample2.mp4"),
    )

    video_frames_data_2 = create_video_with_frames(
        session=test_db,
        collection_id=collection_id,
        video=VideoStub(path="/path/to/sample3.mp4"),
    )

    video_frame_id = video_frames_data.frame_sample_ids[0]
    video_frame_id_1 = video_frames_data_1.frame_sample_ids[0]
    video_frame_id_2 = video_frames_data_2.frame_sample_ids[2]

    # Create annotations labels
    car_label = create_annotation_label(
        session=test_db,
        root_collection_id=collection_id,
        label_name="car",
    )

    airplane_label = create_annotation_label(
        session=test_db,
        root_collection_id=collection_id,
        label_name="airplane",
    )

    create_annotation_label(
        session=test_db,
        root_collection_id=collection_id,
        label_name="house",
    )

    # Create annotations
    create_annotation(
        session=test_db,
        sample_id=video_frame_id,
        annotation_label_id=car_label.annotation_label_id,
        collection_id=collection_id,
    )
    create_annotation(
        session=test_db,
        sample_id=video_frame_id_1,
        annotation_label_id=airplane_label.annotation_label_id,
        collection_id=collection_id,
    )
    create_annotation(
        session=test_db,
        sample_id=video_frame_id_1,
        annotation_label_id=airplane_label.annotation_label_id,
        collection_id=collection_id,
    )
    create_annotation(
        session=test_db,
        sample_id=video_frame_id_2,
        annotation_label_id=airplane_label.annotation_label_id,
        collection_id=collection_id,
    )

    annotations = video_resolver.count_video_frame_annotations_by_video_collection(
        session=test_db,
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
    test_db: Session,
) -> None:
    collection = create_collection(session=test_db, sample_type=SampleType.VIDEO)
    collection_id = collection.collection_id

    # Create videos
    video_frames_data = create_video_with_frames(
        session=test_db,
        collection_id=collection_id,
        video=VideoStub(path="/path/to/sample1.mp4"),
    )

    video_frames_data_1 = create_video_with_frames(
        session=test_db,
        collection_id=collection_id,
        video=VideoStub(path="/path/to/sample2.mp4"),
    )

    video_frames_data_2 = create_video_with_frames(
        session=test_db,
        collection_id=collection_id,
        video=VideoStub(path="/path/to/sample3.mp4"),
    )

    video_frame_id = video_frames_data.frame_sample_ids[0]
    video_frame_id_1 = video_frames_data_1.frame_sample_ids[0]
    video_frame_id_2 = video_frames_data_2.frame_sample_ids[2]

    # Create annotations labels
    car_label = create_annotation_label(
        session=test_db,
        root_collection_id=collection_id,
        label_name="car",
    )

    airplane_label = create_annotation_label(
        session=test_db,
        root_collection_id=collection_id,
        label_name="airplane",
    )

    create_annotation_label(
        session=test_db,
        root_collection_id=collection_id,
        label_name="house",
    )

    # Create annotations
    create_annotation(
        session=test_db,
        sample_id=video_frame_id,
        annotation_label_id=car_label.annotation_label_id,
        collection_id=collection_id,
    )
    create_annotation(
        session=test_db,
        sample_id=video_frame_id_1,
        annotation_label_id=airplane_label.annotation_label_id,
        collection_id=collection_id,
    )
    create_annotation(
        session=test_db,
        sample_id=video_frame_id_1,
        annotation_label_id=airplane_label.annotation_label_id,
        collection_id=collection_id,
    )
    create_annotation(
        session=test_db,
        sample_id=video_frame_id_2,
        annotation_label_id=airplane_label.annotation_label_id,
        collection_id=collection_id,
    )

    annotations = video_resolver.count_video_frame_annotations_by_video_collection(
        session=test_db,
        collection_id=collection_id,
        filters=VideoCountAnnotationsFilter(
            video_frames_annotations_labels=[airplane_label.annotation_label_name]
        ),
    )

    assert len(annotations) == 2

    assert annotations[0].label_name == "airplane"
    assert annotations[0].total_count == 2
    assert annotations[0].current_count == 2

    assert annotations[1].label_name == "car"
    assert annotations[1].total_count == 1
    assert annotations[1].current_count == 0
