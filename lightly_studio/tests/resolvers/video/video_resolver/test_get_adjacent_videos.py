from sqlmodel import Session

from lightly_studio.core.dataset_query.order_by import OrderByField, OrderByMetadataField
from lightly_studio.core.dataset_query.video_sample_field import VideoSampleField
from lightly_studio.models.collection import SampleType
from lightly_studio.resolvers import metadata_resolver, video_resolver
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
        collection_id=collection_id,
    )

    assert result is not None
    assert result.previous_sample_id == video_a.sample_id
    assert result.sample_id == video_b.sample_id
    assert result.next_sample_id == video_c.sample_id
    assert result.current_sample_position == 2
    assert result.total_count == 3


def test_get_adjacent_videos__orders_by_requested_sort(db_session: Session) -> None:
    collection = helpers_resolvers.create_collection(
        session=db_session, sample_type=SampleType.VIDEO
    )
    collection_id = collection.collection_id

    # Widths deliberately disagree with path order so the sort is observable.
    video_a = video_helpers.create_video(
        session=db_session,
        collection_id=collection_id,
        video=video_helpers.VideoStub(path="/videos/a.mp4", width=100),
    )
    video_b = video_helpers.create_video(
        session=db_session,
        collection_id=collection_id,
        video=video_helpers.VideoStub(path="/videos/b.mp4", width=300),
    )
    video_c = video_helpers.create_video(
        session=db_session,
        collection_id=collection_id,
        video=video_helpers.VideoStub(path="/videos/c.mp4", width=200),
    )

    result = video_resolver.get_adjacent_videos(
        session=db_session,
        sample_id=video_c.sample_id,
        collection_id=collection_id,
        order_by=[OrderByField(field=VideoSampleField.width).desc()],
    )

    # Width descending gives b (300), c (200), a (100).
    assert result is not None
    assert result.previous_sample_id == video_b.sample_id
    assert result.sample_id == video_c.sample_id
    assert result.next_sample_id == video_a.sample_id
    assert result.current_sample_position == 2
    assert result.total_count == 3


def test_get_adjacent_videos__orders_by_metadata_sort(db_session: Session) -> None:
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
    # Blur scores deliberately disagree with path order so the metadata sort is observable.
    for video, blur_score in [(video_a, 0.9), (video_b, 0.1), (video_c, 0.5)]:
        metadata_resolver.set_value_for_sample(
            session=db_session,
            sample_id=video.sample_id,
            key="blur_score",
            value=blur_score,
        )

    # Metadata sort adds an outer join to the window query; a multiplied join would
    # corrupt lag/lead/row_number and total_count. Ascending blur gives b, c, a.
    result = video_resolver.get_adjacent_videos(
        session=db_session,
        sample_id=video_c.sample_id,
        collection_id=collection_id,
        order_by=[OrderByMetadataField(field_name="blur_score")],
    )

    assert result is not None
    assert result.previous_sample_id == video_b.sample_id
    assert result.sample_id == video_c.sample_id
    assert result.next_sample_id == video_a.sample_id
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
        collection_id=collection_id,
        filters=VideoFilter(
            sample_filter=SampleFilter(sample_ids=[video_b.sample_id, video_c.sample_id])
        ),
    )

    assert result is not None
    assert result.previous_sample_id == video_b.sample_id
    assert result.sample_id == video_c.sample_id
    assert result.next_sample_id is None
    assert result.current_sample_position == 2
    assert result.total_count == 2


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
        collection_id=collection_id,
        filters=VideoFilter(
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
        set_as_default=True,
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
        collection_id=collection_id,
        text_embedding=[1.0, 1.0],
    )

    assert result is not None
    assert result.previous_sample_id is None
    assert result.sample_id == video_c.sample_id
    assert result.next_sample_id == video_b.sample_id
    assert result.current_sample_position == 1
    assert result.total_count == 3


def test_get_adjacent_videos__similarity_ignores_order_by(db_session: Session) -> None:
    collection = helpers_resolvers.create_collection(
        session=db_session, sample_type=SampleType.VIDEO
    )
    collection_id = collection.collection_id

    embedding_model = helpers_resolvers.create_embedding_model(
        session=db_session,
        collection_id=collection_id,
        embedding_model_name="embedding-for-adjacency",
        embedding_dimension=2,
        set_as_default=True,
    )

    # Widths are chosen so a width-desc sort (a, b, c) disagrees with the similarity
    # order (c, b, a); the anchor's neighbours reveal which one the resolver applies.
    video_a = video_helpers.create_video(
        session=db_session,
        collection_id=collection_id,
        video=video_helpers.VideoStub(path="/videos/a.mp4", width=300),
    )
    video_b = video_helpers.create_video(
        session=db_session,
        collection_id=collection_id,
        video=video_helpers.VideoStub(path="/videos/b.mp4", width=200),
    )
    video_c = video_helpers.create_video(
        session=db_session,
        collection_id=collection_id,
        video=video_helpers.VideoStub(path="/videos/c.mp4", width=100),
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
        collection_id=collection_id,
        text_embedding=[1.0, 1.0],
        order_by=[OrderByField(field=VideoSampleField.width).desc()],
    )

    # Similarity wins: neighbours follow distance (c, b, a), not width-desc (a, b, c).
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
        collection_id=collection_1.collection_id,
    )

    assert result is None
