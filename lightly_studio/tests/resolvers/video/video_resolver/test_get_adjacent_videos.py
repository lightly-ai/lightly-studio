import pytest
from sqlmodel import Session

from lightly_studio.models.collection import SampleType
from lightly_studio.resolvers import video_resolver
from lightly_studio.resolvers.annotations.annotations_filter import AnnotationsFilter
from lightly_studio.resolvers.sample_resolver.sample_filter import SampleFilter
from lightly_studio.resolvers.video_resolver.video_filter import VideoFilter
from tests import helpers_resolvers
from tests.resolvers.video import helpers as video_helpers


def test_get_adjacent_videos__orders_by_path(db_session: Session) -> None:
    collection = helpers_resolvers.create_collection(
        session=db_session, sample_type=SampleType.VIDEO
    )
    collection_id = collection.collection_id

    video_a = video_helpers.create_video(
        session=db_session,
        collection_id=collection_id,
        video=video_helpers.VideoStub(path="/videos/a.mp4"),
    )
    video_b = video_helpers.create_video(
        session=db_session,
        collection_id=collection_id,
        video=video_helpers.VideoStub(path="/videos/b.mp4"),
    )
    video_c = video_helpers.create_video(
        session=db_session,
        collection_id=collection_id,
        video=video_helpers.VideoStub(path="/videos/c.mp4"),
    )

    result = video_resolver.get_adjacent_videos(
        session=db_session,
        sample_id=video_b.sample_id,
        filters=VideoFilter(sample_filter=SampleFilter(collection_id=collection_id)),
    )

    assert result is not None
    assert result.previous_sample_id == video_a.sample_id
    assert result.sample_id == video_b.sample_id
    assert result.next_sample_id == video_c.sample_id
    assert result.current_sample_position == 2
    assert result.total_count == 3


def test_get_adjacent_videos__respects_sample_ids(db_session: Session) -> None:
    collection = helpers_resolvers.create_collection(
        session=db_session, sample_type=SampleType.VIDEO
    )
    collection_id = collection.collection_id

    video_helpers.create_video(
        session=db_session,
        collection_id=collection_id,
        video=video_helpers.VideoStub(path="/videos/a.mp4"),
    )
    video_b = video_helpers.create_video(
        session=db_session,
        collection_id=collection_id,
        video=video_helpers.VideoStub(path="/videos/b.mp4"),
    )
    video_c = video_helpers.create_video(
        session=db_session,
        collection_id=collection_id,
        video=video_helpers.VideoStub(path="/videos/c.mp4"),
    )

    result = video_resolver.get_adjacent_videos(
        session=db_session,
        sample_id=video_c.sample_id,
        filters=VideoFilter(
            sample_filter=SampleFilter(
                collection_id=collection_id, sample_ids=[video_b.sample_id, video_c.sample_id]
            )
        ),
    )

    assert result is not None
    assert result.previous_sample_id == video_b.sample_id
    assert result.sample_id == video_c.sample_id
    assert result.next_sample_id is None
    assert result.current_sample_position == 2
    assert result.total_count == 2


def test_get_adjacent_videos__raises_with_filter_missing_collection_id(db_session: Session) -> None:
    collection = helpers_resolvers.create_collection(
        session=db_session, sample_type=SampleType.VIDEO
    )
    collection_id = collection.collection_id

    video = video_helpers.create_video(
        session=db_session,
        collection_id=collection_id,
        video=video_helpers.VideoStub(path="/videos/a.mp4"),
    )

    with pytest.raises(ValueError, match=r"Collection ID must be provided in filters."):
        video_resolver.get_adjacent_videos(
            session=db_session,
            sample_id=video.sample_id,
            filters=VideoFilter(sample_filter=SampleFilter()),
        )


def test_get_adjacent_videos__respects_annotation_filter(db_session: Session) -> None:
    collection = helpers_resolvers.create_collection(
        session=db_session, sample_type=SampleType.VIDEO
    )
    collection_id = collection.collection_id

    dog_label = helpers_resolvers.create_annotation_label(
        session=db_session,
        root_collection_id=collection_id,
        label_name="dog",
    )
    cat_label = helpers_resolvers.create_annotation_label(
        session=db_session,
        root_collection_id=collection_id,
        label_name="cat",
    )

    video_a = video_helpers.create_video_with_frames(
        session=db_session,
        collection_id=collection_id,
        video=video_helpers.VideoStub(path="/videos/a.mp4", duration_s=1.0, fps=1.0),
    )
    video_b = video_helpers.create_video_with_frames(
        session=db_session,
        collection_id=collection_id,
        video=video_helpers.VideoStub(path="/videos/b.mp4", duration_s=1.0, fps=1.0),
    )
    video_c = video_helpers.create_video_with_frames(
        session=db_session,
        collection_id=collection_id,
        video=video_helpers.VideoStub(path="/videos/c.mp4", duration_s=1.0, fps=1.0),
    )

    helpers_resolvers.create_annotations(
        session=db_session,
        collection_id=video_a.video_frames_collection_id,
        annotations=[
            helpers_resolvers.AnnotationDetails(
                sample_id=video_a.frame_sample_ids[0],
                annotation_label_id=dog_label.annotation_label_id,
            ),
            helpers_resolvers.AnnotationDetails(
                sample_id=video_b.frame_sample_ids[0],
                annotation_label_id=dog_label.annotation_label_id,
            ),
            helpers_resolvers.AnnotationDetails(
                sample_id=video_c.frame_sample_ids[0],
                annotation_label_id=cat_label.annotation_label_id,
            ),
        ],
    )

    result = video_resolver.get_adjacent_videos(
        session=db_session,
        sample_id=video_b.video_sample_id,
        filters=VideoFilter(
            sample_filter=SampleFilter(
                collection_id=collection_id,
            ),
            frame_annotation_filter=AnnotationsFilter(
                annotation_label_ids=[dog_label.annotation_label_id]
            ),
        ),
    )

    assert result is not None
    assert result.previous_sample_id == video_a.video_sample_id
    assert result.sample_id == video_b.video_sample_id
    assert result.next_sample_id is None
    assert result.current_sample_position == 2
    assert result.total_count == 2


def test_get_adjacent_videos__with_similarity(db_session: Session) -> None:
    collection = helpers_resolvers.create_collection(
        session=db_session, sample_type=SampleType.VIDEO
    )
    collection_id = collection.collection_id

    embedding_model = helpers_resolvers.create_embedding_model(
        session=db_session,
        collection_id=collection_id,
        embedding_model_name="embedding-for-adjacency",
        embedding_dimension=2,
    )

    video_a = video_helpers.create_video(
        session=db_session,
        collection_id=collection_id,
        video=video_helpers.VideoStub(path="/videos/a.mp4"),
    )
    video_b = video_helpers.create_video(
        session=db_session,
        collection_id=collection_id,
        video=video_helpers.VideoStub(path="/videos/b.mp4"),
    )
    video_c = video_helpers.create_video(
        session=db_session,
        collection_id=collection_id,
        video=video_helpers.VideoStub(path="/videos/c.mp4"),
    )

    helpers_resolvers.create_sample_embedding(
        session=db_session,
        sample_id=video_a.sample_id,
        embedding_model_id=embedding_model.embedding_model_id,
        embedding=[0.0, 1.0],
    )
    helpers_resolvers.create_sample_embedding(
        session=db_session,
        sample_id=video_b.sample_id,
        embedding_model_id=embedding_model.embedding_model_id,
        embedding=[0.5, 1.0],
    )
    helpers_resolvers.create_sample_embedding(
        session=db_session,
        sample_id=video_c.sample_id,
        embedding_model_id=embedding_model.embedding_model_id,
        embedding=[1.0, 1.0],
    )

    result = video_resolver.get_adjacent_videos(
        session=db_session,
        sample_id=video_c.sample_id,
        filters=VideoFilter(
            sample_filter=SampleFilter(
                collection_id=collection_id,
            )
        ),
        text_embedding=[1.0, 1.0],
    )

    assert result is not None
    assert result.previous_sample_id is None
    assert result.sample_id == video_c.sample_id
    assert result.next_sample_id == video_b.sample_id
    assert result.current_sample_position == 1
    assert result.total_count == 3


def test_get_adjacent_videos__returns_none_when_sample_not_in_filter(db_session: Session) -> None:
    collection = helpers_resolvers.create_collection(
        session=db_session, sample_type=SampleType.VIDEO
    )
    collection_1 = helpers_resolvers.create_collection(
        session=db_session, collection_name="collection_1", sample_type=SampleType.VIDEO
    )

    video_a = video_helpers.create_video(
        session=db_session,
        collection_id=collection.collection_id,
        video=video_helpers.VideoStub(path="/videos/a.mp4"),
    )

    # Use a filter that includes only samples from collection_1,
    # which does not include video_a.sample_id
    result = video_resolver.get_adjacent_videos(
        session=db_session,
        sample_id=video_a.sample_id,
        filters=VideoFilter(
            sample_filter=SampleFilter(
                collection_id=collection_1.collection_id,
                sample_ids=[],
            )
        ),
    )

    assert result is None
