import pytest
from sqlmodel import Session

from lightly_studio.models.collection import SampleType
from lightly_studio.resolvers import video_frame_resolver
from lightly_studio.resolvers.sample_resolver.sample_filter import SampleFilter
from lightly_studio.resolvers.video_frame_resolver.video_frame_filter import VideoFrameFilter
from tests import helpers_resolvers
from tests.resolvers.video import helpers as video_helpers


def test_get_adjacent_video_frames__orders_by_path_and_frame_number(test_db: Session) -> None:
    collection = helpers_resolvers.create_collection(session=test_db, sample_type=SampleType.VIDEO)

    video_frames_a = video_helpers.create_video_with_frames(
        session=test_db,
        collection_id=collection.collection_id,
        video=video_helpers.VideoStub(path="/videos/a.mp4", fps=1, duration_s=3.0),
    )
    video_frames_b = video_helpers.create_video_with_frames(
        session=test_db,
        collection_id=collection.collection_id,
        video=video_helpers.VideoStub(path="/videos/b.mp4", fps=1, duration_s=2.0),
    )

    frame_collection_id = video_frames_a.video_frames_collection_id
    filters = VideoFrameFilter(sample_filter=SampleFilter(collection_id=frame_collection_id))

    target_frame_id = video_frames_a.frame_sample_ids[1]

    result = video_frame_resolver.get_adjacent_video_frames(
        session=test_db,
        sample_id=target_frame_id,
        filters=filters,
    )

    assert result.previous_sample_id == video_frames_a.frame_sample_ids[0]
    assert result.sample_id == target_frame_id
    assert result.next_sample_id == video_frames_a.frame_sample_ids[2]
    assert result.current_sample_position == 2
    assert result.total_count == len(video_frames_a.frame_sample_ids) + len(
        video_frames_b.frame_sample_ids
    )


def test_get_adjacent_video_frames__respects_sample_ids(test_db: Session) -> None:
    collection = helpers_resolvers.create_collection(session=test_db, sample_type=SampleType.VIDEO)
    video_frames = video_helpers.create_video_with_frames(
        session=test_db,
        collection_id=collection.collection_id,
        video=video_helpers.VideoStub(path="/videos/a.mp4", fps=1, duration_s=3.0),
    )

    frame_collection_id = video_frames.video_frames_collection_id
    sample_ids = [
        video_frames.frame_sample_ids[1],
        video_frames.frame_sample_ids[2],
    ]
    filters = VideoFrameFilter(
        sample_filter=SampleFilter(collection_id=frame_collection_id, sample_ids=sample_ids),
    )

    target_frame_id = video_frames.frame_sample_ids[2]

    result = video_frame_resolver.get_adjacent_video_frames(
        session=test_db,
        sample_id=target_frame_id,
        filters=filters,
    )

    assert result.previous_sample_id == video_frames.frame_sample_ids[1]
    assert result.sample_id == target_frame_id
    assert result.next_sample_id is None
    assert result.current_sample_position == 2
    assert result.total_count == len(sample_ids)


def test_get_adjacent_video_frames__raises_without_collection_id(test_db: Session) -> None:
    collection = helpers_resolvers.create_collection(session=test_db, sample_type=SampleType.VIDEO)
    video_frames = video_helpers.create_video_with_frames(
        session=test_db,
        collection_id=collection.collection_id,
        video=video_helpers.VideoStub(path="/videos/a.mp4", fps=1, duration_s=1.0),
    )

    with pytest.raises(ValueError, match="Collection ID must be provided in filters."):
        video_frame_resolver.get_adjacent_video_frames(
            session=test_db,
            sample_id=video_frames.frame_sample_ids[0],
            filters=VideoFrameFilter(sample_filter=SampleFilter()),
        )


def test_get_adjacent_video_frames__respects_annotation_filter(test_db: Session) -> None:
    collection = helpers_resolvers.create_collection(session=test_db, sample_type=SampleType.VIDEO)

    video_frames = video_helpers.create_video_with_frames(
        session=test_db,
        collection_id=collection.collection_id,
        video=video_helpers.VideoStub(path="/videos/a.mp4", fps=1, duration_s=3.0),
    )

    frame_collection_id = video_frames.video_frames_collection_id

    dog_label = helpers_resolvers.create_annotation_label(
        session=test_db,
        dataset_id=frame_collection_id,
        label_name="dog",
    )
    cat_label = helpers_resolvers.create_annotation_label(
        session=test_db,
        dataset_id=frame_collection_id,
        label_name="cat",
    )

    helpers_resolvers.create_annotations(
        session=test_db,
        collection_id=frame_collection_id,
        annotations=[
            helpers_resolvers.AnnotationDetails(
                sample_id=video_frames.frame_sample_ids[0],
                annotation_label_id=dog_label.annotation_label_id,
            ),
            helpers_resolvers.AnnotationDetails(
                sample_id=video_frames.frame_sample_ids[1],
                annotation_label_id=dog_label.annotation_label_id,
            ),
            helpers_resolvers.AnnotationDetails(
                sample_id=video_frames.frame_sample_ids[2],
                annotation_label_id=cat_label.annotation_label_id,
            ),
        ],
    )

    filters = VideoFrameFilter(
        sample_filter=SampleFilter(
            collection_id=frame_collection_id,
            annotation_label_ids=[dog_label.annotation_label_id],
        )
    )

    result = video_frame_resolver.get_adjacent_video_frames(
        session=test_db,
        sample_id=video_frames.frame_sample_ids[1],
        filters=filters,
    )

    assert result.previous_sample_id == video_frames.frame_sample_ids[0]
    assert result.sample_id == video_frames.frame_sample_ids[1]
    assert result.next_sample_id is None
    assert result.current_sample_position == 2
    assert result.total_count == 2
