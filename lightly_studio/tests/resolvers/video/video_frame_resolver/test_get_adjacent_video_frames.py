import pytest
from sqlmodel import Session

from lightly_studio.models.collection import SampleType
from lightly_studio.models.video import VideoFrameCreate
from lightly_studio.resolvers import tag_resolver, video_frame_resolver
from lightly_studio.resolvers.sample_resolver.sample_filter import SampleFilter
from lightly_studio.resolvers.video_frame_resolver import VideoFrameAdjacentFilter
from lightly_studio.resolvers.video_frame_resolver.video_frame_filter import VideoFrameFilter
from lightly_studio.resolvers.video_resolver.video_filter import VideoFilter
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

    target_frame_id = video_frames_a.frame_sample_ids[-1]

    result = video_frame_resolver.get_adjacent_video_frames(
        session=test_db,
        sample_id=target_frame_id,
        filters=VideoFrameAdjacentFilter(
            video_frame_filter=VideoFrameFilter(
                sample_filter=SampleFilter(collection_id=frame_collection_id),
            )
        ),
    )

    assert result is not None
    assert result.previous_sample_id == video_frames_a.frame_sample_ids[-2]
    assert result.sample_id == target_frame_id
    assert result.next_sample_id == video_frames_b.frame_sample_ids[0]
    assert result.current_sample_position == len(video_frames_a.frame_sample_ids)
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

    target_frame_id = video_frames.frame_sample_ids[2]

    result = video_frame_resolver.get_adjacent_video_frames(
        session=test_db,
        sample_id=target_frame_id,
        filters=VideoFrameAdjacentFilter(
            video_frame_filter=VideoFrameFilter(
                sample_filter=SampleFilter(
                    collection_id=frame_collection_id, sample_ids=sample_ids
                ),
            )
        ),
    )

    assert result is not None
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

    with pytest.raises(
        ValueError, match="Collection ID must be provided in video_frame_filter.sample_filter."
    ):
        video_frame_resolver.get_adjacent_video_frames(
            session=test_db,
            sample_id=video_frames.frame_sample_ids[0],
            filters=VideoFrameAdjacentFilter(
                video_frame_filter=VideoFrameFilter(sample_filter=SampleFilter())
            ),
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

    result = video_frame_resolver.get_adjacent_video_frames(
        session=test_db,
        sample_id=video_frames.frame_sample_ids[1],
        filters=VideoFrameAdjacentFilter(
            video_frame_filter=VideoFrameFilter(
                sample_filter=SampleFilter(
                    collection_id=frame_collection_id,
                    annotation_label_ids=[dog_label.annotation_label_id],
                )
            )
        ),
    )

    assert result is not None
    assert result.previous_sample_id == video_frames.frame_sample_ids[0]
    assert result.sample_id == video_frames.frame_sample_ids[1]
    assert result.next_sample_id is None
    assert result.current_sample_position == 2
    assert result.total_count == 2


def test_get_adjacent_video_frames__filters_by_parent_video_filter(test_db: Session) -> None:
    collection = helpers_resolvers.create_collection(session=test_db, sample_type=SampleType.VIDEO)

    video_a = video_helpers.create_video_with_frames(
        session=test_db,
        collection_id=collection.collection_id,
        video=video_helpers.VideoStub(path="/videos/a.mp4", fps=1, duration_s=2.0),
    )
    video_b = video_helpers.create_video_with_frames(
        session=test_db,
        collection_id=collection.collection_id,
        video=video_helpers.VideoStub(path="/videos/b.mp4", fps=1, duration_s=2.0),
    )

    result = video_frame_resolver.get_adjacent_video_frames(
        session=test_db,
        sample_id=video_b.frame_sample_ids[1],
        filters=VideoFrameAdjacentFilter(
            video_frame_filter=VideoFrameFilter(
                sample_filter=SampleFilter(
                    collection_id=video_a.video_frames_collection_id,
                )
            ),
            video_filter=VideoFilter(
                sample_filter=SampleFilter(
                    collection_id=collection.collection_id,
                    sample_ids=[video_b.video_sample_id],
                )
            ),
        ),
    )

    assert result is not None
    assert result.previous_sample_id == video_b.frame_sample_ids[0]
    assert result.sample_id == video_b.frame_sample_ids[1]
    assert result.next_sample_id is None
    assert result.current_sample_position == 2
    assert result.total_count == len(video_b.frame_sample_ids)


def test_get_adjacent_video_frames__filters_by_parent_video_tags(test_db: Session) -> None:
    collection = helpers_resolvers.create_collection(session=test_db, sample_type=SampleType.VIDEO)

    video_a = video_helpers.create_video_with_frames(
        session=test_db,
        collection_id=collection.collection_id,
        video=video_helpers.VideoStub(path="/videos/a.mp4", fps=1, duration_s=2.0),
    )
    video_b = video_helpers.create_video_with_frames(
        session=test_db,
        collection_id=collection.collection_id,
        video=video_helpers.VideoStub(path="/videos/b.mp4", fps=1, duration_s=2.0),
    )

    tag = helpers_resolvers.create_tag(
        session=test_db,
        collection_id=collection.collection_id,
        tag_name="keep",
    )

    tag_resolver.add_sample_ids_to_tag_id(
        session=test_db, tag_id=tag.tag_id, sample_ids=[video_b.video_sample_id]
    )

    result = video_frame_resolver.get_adjacent_video_frames(
        session=test_db,
        sample_id=video_b.frame_sample_ids[-1],
        filters=VideoFrameAdjacentFilter(
            video_frame_filter=VideoFrameFilter(
                sample_filter=SampleFilter(
                    collection_id=video_a.video_frames_collection_id,
                )
            ),
            video_filter=VideoFilter(
                sample_filter=SampleFilter(
                    collection_id=collection.collection_id,
                    tag_ids=[tag.tag_id],
                )
            ),
        ),
    )

    assert result is not None
    assert result.previous_sample_id == video_b.frame_sample_ids[-2]
    assert result.sample_id == video_b.frame_sample_ids[-1]
    assert result.next_sample_id is None
    assert result.current_sample_position == len(video_b.frame_sample_ids)
    assert result.total_count == len(video_b.frame_sample_ids)


def test_get_adjacent_video_frames__filters_by_parent_video_annotations(test_db: Session) -> None:
    collection = helpers_resolvers.create_collection(session=test_db, sample_type=SampleType.VIDEO)

    video_a = video_helpers.create_video_with_frames(
        session=test_db,
        collection_id=collection.collection_id,
        video=video_helpers.VideoStub(path="/videos/a.mp4", fps=1, duration_s=2.0),
    )
    video_b = video_helpers.create_video_with_frames(
        session=test_db,
        collection_id=collection.collection_id,
        video=video_helpers.VideoStub(path="/videos/b.mp4", fps=1, duration_s=2.0),
    )

    label = helpers_resolvers.create_annotation_label(
        session=test_db,
        dataset_id=video_a.video_frames_collection_id,
        label_name="keep-me",
    )
    helpers_resolvers.create_annotations(
        session=test_db,
        collection_id=video_a.video_frames_collection_id,
        annotations=[
            helpers_resolvers.AnnotationDetails(
                sample_id=video_b.frame_sample_ids[0],
                annotation_label_id=label.annotation_label_id,
            ),
            helpers_resolvers.AnnotationDetails(
                sample_id=video_b.frame_sample_ids[1],
                annotation_label_id=label.annotation_label_id,
            ),
        ],
    )

    result = video_frame_resolver.get_adjacent_video_frames(
        session=test_db,
        sample_id=video_b.frame_sample_ids[1],
        filters=VideoFrameAdjacentFilter(
            video_frame_filter=VideoFrameFilter(
                sample_filter=SampleFilter(
                    collection_id=video_a.video_frames_collection_id,
                )
            ),
            video_filter=VideoFilter(
                annotation_frames_label_ids=[label.annotation_label_id],
                sample_filter=SampleFilter(
                    collection_id=collection.collection_id,
                ),
            ),
        ),
    )

    assert result is not None
    assert result.previous_sample_id == video_b.frame_sample_ids[0]
    assert result.sample_id == video_b.frame_sample_ids[1]
    assert result.next_sample_id is None
    assert result.current_sample_position == 2
    assert result.total_count == len(video_b.frame_sample_ids)


def test_get_adjacent_video_frames__uses_video_text_embedding(test_db: Session) -> None:
    collection = helpers_resolvers.create_collection(session=test_db, sample_type=SampleType.VIDEO)

    embedding_model = helpers_resolvers.create_embedding_model(
        session=test_db,
        collection_id=collection.collection_id,
        embedding_model_name="video-text-embedding",
        embedding_dimension=2,
    )

    video_a = video_helpers.create_video_with_frames(
        session=test_db,
        collection_id=collection.collection_id,
        video=video_helpers.VideoStub(path="/videos/a.mp4", duration_s=1.0, fps=1),
    )
    video_b = video_helpers.create_video_with_frames(
        session=test_db,
        collection_id=collection.collection_id,
        video=video_helpers.VideoStub(path="/videos/b.mp4", duration_s=1.0, fps=1),
    )
    video_c = video_helpers.create_video_with_frames(
        session=test_db,
        collection_id=collection.collection_id,
        video=video_helpers.VideoStub(path="/videos/c.mp4", duration_s=1.0, fps=1),
    )

    helpers_resolvers.create_sample_embedding(
        session=test_db,
        sample_id=video_a.video_sample_id,
        embedding_model_id=embedding_model.embedding_model_id,
        embedding=[0.0, 1.0],
    )
    helpers_resolvers.create_sample_embedding(
        session=test_db,
        sample_id=video_b.video_sample_id,
        embedding_model_id=embedding_model.embedding_model_id,
        embedding=[0.5, 1.0],
    )
    helpers_resolvers.create_sample_embedding(
        session=test_db,
        sample_id=video_c.video_sample_id,
        embedding_model_id=embedding_model.embedding_model_id,
        embedding=[1.0, 1.0],
    )

    result = video_frame_resolver.get_adjacent_video_frames(
        session=test_db,
        sample_id=video_c.frame_sample_ids[0],
        filters=VideoFrameAdjacentFilter(
            video_frame_filter=VideoFrameFilter(
                sample_filter=SampleFilter(collection_id=video_a.video_frames_collection_id),
            ),
            video_filter=VideoFilter(
                sample_filter=SampleFilter(collection_id=collection.collection_id)
            ),
            video_text_embedding=[1.0, 1.0],
        ),
    )

    assert result is not None
    assert result.previous_sample_id is None
    assert result.sample_id == video_c.frame_sample_ids[0]
    assert result.next_sample_id == video_b.frame_sample_ids[0]
    assert result.current_sample_position == 1
    assert result.total_count == 3


def test_get_adjacent_video_frames__requires_resolvable_collection_for_text_embedding(
    test_db: Session,
) -> None:
    video_collection = helpers_resolvers.create_collection(
        session=test_db, sample_type=SampleType.VIDEO
    )
    video = video_helpers.create_video(
        session=test_db,
        collection_id=video_collection.collection_id,
        video=video_helpers.VideoStub(),
    )

    frame_collection = helpers_resolvers.create_collection(
        session=test_db, sample_type=SampleType.VIDEO_FRAME
    )

    frame_sample_id = video_frame_resolver.create_many(
        session=test_db,
        collection_id=frame_collection.collection_id,
        samples=[
            VideoFrameCreate(
                frame_number=0,
                frame_timestamp_s=0.0,
                frame_timestamp_pts=0,
                parent_sample_id=video.sample_id,
            )
        ],
    )[0]

    with pytest.raises(
        ValueError, match="Collection ID must be resolvable when video_text_embedding is provided."
    ):
        video_frame_resolver.get_adjacent_video_frames(
            session=test_db,
            sample_id=frame_sample_id,
            filters=VideoFrameAdjacentFilter(
                video_frame_filter=VideoFrameFilter(
                    sample_filter=SampleFilter(collection_id=frame_collection.collection_id),
                ),
                video_text_embedding=[0.1, 0.2],
            ),
        )


def test_get_adjacent_video_frames__returns_none_when_sample_not_in_filter(
    test_db: Session,
) -> None:
    collection = helpers_resolvers.create_collection(session=test_db, sample_type=SampleType.VIDEO)
    collection_1 = helpers_resolvers.create_collection(
        session=test_db, collection_name="collection_1", sample_type=SampleType.VIDEO
    )

    video_frames = video_helpers.create_video_with_frames(
        session=test_db,
        collection_id=collection.collection_id,
        video=video_helpers.VideoStub(path="/videos/a.mp4", fps=1, duration_s=3.0),
    )

    result = video_frame_resolver.get_adjacent_video_frames(
        session=test_db,
        sample_id=video_frames.frame_sample_ids[1],
        filters=VideoFrameAdjacentFilter(
            video_frame_filter=VideoFrameFilter(
                sample_filter=SampleFilter(
                    collection_id=collection_1.collection_id,
                )
            )
        ),
    )

    assert result is None
