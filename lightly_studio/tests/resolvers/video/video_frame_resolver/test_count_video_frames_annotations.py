from sqlmodel import Session

from lightly_studio.models.collection import SampleType
from lightly_studio.resolvers import video_frame_resolver
from lightly_studio.resolvers.annotations.annotations_filter import AnnotationsFilter
from lightly_studio.resolvers.sample_resolver.sample_filter import SampleFilter
from lightly_studio.resolvers.video_frame_resolver.video_frame_filter import VideoFrameFilter
from tests.helpers_resolvers import create_annotation, create_annotation_label, create_collection
from tests.resolvers.video.helpers import VideoStub, create_video_with_frames


def test_get_video_frames_count_annotation_views_without_filter(db_session: Session) -> None:
    collection = create_collection(session=db_session, sample_type=SampleType.VIDEO)

    video_frames_data = create_video_with_frames(
        session=db_session,
        collection_id=collection.collection_id,
        video=VideoStub(path="/path/to/sample1.mp4"),
    )

    # Create annotation labels
    car_label = create_annotation_label(
        session=db_session, dataset_id=collection.collection_id, label_name="car"
    )
    airplane_label = create_annotation_label(
        session=db_session, dataset_id=collection.collection_id, label_name="airplane"
    )
    create_annotation_label(
        session=db_session, dataset_id=collection.collection_id, label_name="house"
    )

    # Create annotations
    create_annotation(
        session=db_session,
        sample_id=video_frames_data.frame_sample_ids[0],
        annotation_label_id=car_label.annotation_label_id,
        collection_id=video_frames_data.video_frames_collection_id,
    )
    create_annotation(
        session=db_session,
        sample_id=video_frames_data.frame_sample_ids[1],
        annotation_label_id=airplane_label.annotation_label_id,
        collection_id=video_frames_data.video_frames_collection_id,
    )
    create_annotation(
        session=db_session,
        sample_id=video_frames_data.frame_sample_ids[1],
        annotation_label_id=airplane_label.annotation_label_id,
        collection_id=video_frames_data.video_frames_collection_id,
    )

    annotations = video_frame_resolver.get_video_frames_count_annotation_views(
        session=db_session,
        collection_id=video_frames_data.video_frames_collection_id,
    )

    assert len(annotations) == 2

    assert annotations[0].label_name == "airplane"
    assert annotations[0].total_count == 2
    assert annotations[0].current_count == 2

    assert annotations[1].label_name == "car"
    assert annotations[1].total_count == 1
    assert annotations[1].current_count == 1


def test_get_video_frames_count_annotation_views_without_annotations_filter(
    db_session: Session,
) -> None:
    collection = create_collection(session=db_session, sample_type=SampleType.VIDEO)

    video_frames_data = create_video_with_frames(
        session=db_session,
        collection_id=collection.collection_id,
        video=VideoStub(path="/path/to/sample1.mp4"),
    )

    # Create annotation labels
    car_label = create_annotation_label(
        session=db_session, dataset_id=collection.collection_id, label_name="car"
    )
    airplane_label = create_annotation_label(
        session=db_session, dataset_id=collection.collection_id, label_name="airplane"
    )
    create_annotation_label(
        session=db_session, dataset_id=collection.collection_id, label_name="house"
    )

    # Create annotations
    create_annotation(
        session=db_session,
        sample_id=video_frames_data.frame_sample_ids[0],
        annotation_label_id=car_label.annotation_label_id,
        collection_id=video_frames_data.video_frames_collection_id,
    )
    create_annotation(
        session=db_session,
        sample_id=video_frames_data.frame_sample_ids[1],
        annotation_label_id=airplane_label.annotation_label_id,
        collection_id=video_frames_data.video_frames_collection_id,
    )
    create_annotation(
        session=db_session,
        sample_id=video_frames_data.frame_sample_ids[1],
        annotation_label_id=airplane_label.annotation_label_id,
        collection_id=video_frames_data.video_frames_collection_id,
    )

    annotations = video_frame_resolver.get_video_frames_count_annotation_views(
        session=db_session,
        collection_id=video_frames_data.video_frames_collection_id,
        filters=VideoFrameFilter(
            sample_filter=SampleFilter(
                annotations_filter=AnnotationsFilter(
                    annotation_label_ids=[airplane_label.annotation_label_id]
                )
            )
        ),
    )

    assert len(annotations) == 2

    assert annotations[0].label_name == "airplane"
    assert annotations[0].total_count == 2
    assert annotations[0].current_count == 2

    assert annotations[1].label_name == "car"
    assert annotations[1].total_count == 1
    assert annotations[1].current_count == 0
