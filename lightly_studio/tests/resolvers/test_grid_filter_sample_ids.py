from pytest_mock import MockerFixture
from sqlmodel import Session

from lightly_studio.models.collection import SampleType
from lightly_studio.models.embedding_region import EmbeddingRegion, Point2D
from lightly_studio.resolvers import embedding_region_resolver, grid_filter_sample_ids
from lightly_studio.resolvers.sample_resolver.sample_filter import SampleFilter
from lightly_studio.resolvers.video_resolver.video_filter import VideoFilter
from tests.helpers_resolvers import create_collection
from tests.resolvers.video.helpers import VideoStub, create_videos


def test_build_sample_ids_query__video_embedding_region(
    db_session: Session, mocker: MockerFixture
) -> None:
    collection = create_collection(session=db_session, sample_type=SampleType.VIDEO)
    video_ids = create_videos(
        session=db_session,
        collection_id=collection.collection_id,
        videos=[VideoStub(path="/path/to/a.mp4"), VideoStub(path="/path/to/b.mp4")],
    )
    mocker.patch.object(
        embedding_region_resolver,
        "get_sample_ids_in_region",
        return_value=[video_ids[1]],
    )
    video_filter = VideoFilter(
        sample_filter=SampleFilter(
            embedding_region=EmbeddingRegion(
                polygon=[Point2D(x=0, y=0), Point2D(x=1, y=0), Point2D(x=1, y=1)]
            )
        )
    )

    query = grid_filter_sample_ids.build_sample_ids_query(
        session=db_session,
        collection_id=collection.collection_id,
        grid_filter=video_filter,
    )

    assert set(db_session.exec(query).all()) == {video_ids[1]}
    assert video_filter.sample_filter is not None
    assert video_filter.sample_filter.region_sample_ids == [video_ids[1]]
