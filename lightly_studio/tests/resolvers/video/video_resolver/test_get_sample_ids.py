from __future__ import annotations

from pytest_mock import MockerFixture
from sqlmodel import Session

from lightly_studio.models.collection import SampleType
from lightly_studio.models.embedding_region import EmbeddingRegion, Point2D
from lightly_studio.resolvers import embedding_region_resolver, video_resolver
from lightly_studio.resolvers.image_filter import FilterDimensions
from lightly_studio.resolvers.sample_resolver.sample_filter import SampleFilter
from lightly_studio.resolvers.video_resolver.video_filter import VideoFilter
from tests.helpers_resolvers import create_collection
from tests.resolvers.video.helpers import VideoStub, create_videos


def test_get_sample_ids(db_session: Session) -> None:
    collection = create_collection(session=db_session, sample_type=SampleType.VIDEO)
    other_collection = create_collection(session=db_session, sample_type=SampleType.VIDEO)

    created_video_ids = create_videos(
        session=db_session,
        collection_id=collection.collection_id,
        videos=[
            VideoStub(path="/path/to/small.mp4", width=100, height=100),
            VideoStub(path="/path/to/large.mp4", width=800, height=800),
        ],
    )
    create_videos(
        session=db_session,
        collection_id=other_collection.collection_id,
        videos=[VideoStub(path="/path/to/other.mp4", width=800, height=800)],
    )

    all_sample_ids = video_resolver.get_sample_ids(
        session=db_session,
        collection_id=collection.collection_id,
    )
    assert all_sample_ids == set(created_video_ids)

    filtered_sample_ids = video_resolver.get_sample_ids(
        session=db_session,
        collection_id=collection.collection_id,
        filters=VideoFilter(
            width=FilterDimensions(min=500),
        ),
    )
    assert filtered_sample_ids == {created_video_ids[1]}


def test_build_sample_ids_query(db_session: Session) -> None:
    collection = create_collection(session=db_session, sample_type=SampleType.VIDEO)
    other_collection = create_collection(session=db_session, sample_type=SampleType.VIDEO)

    created_video_ids = create_videos(
        session=db_session,
        collection_id=collection.collection_id,
        videos=[
            VideoStub(path="/path/to/small.mp4", width=100, height=100),
            VideoStub(path="/path/to/large.mp4", width=800, height=800),
        ],
    )
    create_videos(
        session=db_session,
        collection_id=other_collection.collection_id,
        videos=[VideoStub(path="/path/to/other.mp4", width=800, height=800)],
    )

    query = video_resolver.build_sample_ids_query(collection_id=collection.collection_id)
    assert set(db_session.exec(query).all()) == set(created_video_ids)

    filtered_query = video_resolver.build_sample_ids_query(
        collection_id=collection.collection_id,
        filters=VideoFilter(width=FilterDimensions(min=500)),
    )
    assert set(db_session.exec(filtered_query).all()) == {created_video_ids[1]}


def test_get_sample_ids__with_embedding_region(
    db_session: Session, mocker: MockerFixture
) -> None:
    collection = create_collection(session=db_session, sample_type=SampleType.VIDEO)
    video_ids = create_videos(
        session=db_session,
        collection_id=collection.collection_id,
        videos=[VideoStub(path="/path/to/a.mp4"), VideoStub(path="/path/to/b.mp4")],
    )
    region = EmbeddingRegion(
        polygon=[Point2D(x=0, y=0), Point2D(x=1, y=0), Point2D(x=1, y=1)]
    )
    mocker.patch.object(
        embedding_region_resolver, "get_sample_ids_in_region", return_value=[video_ids[1]]
    )

    result = video_resolver.get_sample_ids(
        session=db_session,
        collection_id=collection.collection_id,
        filters=VideoFilter(sample_filter=SampleFilter(embedding_region=region)),
    )

    assert result == {video_ids[1]}
