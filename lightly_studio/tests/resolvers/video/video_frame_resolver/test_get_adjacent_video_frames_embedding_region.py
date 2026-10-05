import pytest
from pytest_mock import MockerFixture
from sqlmodel import Session

from lightly_studio.models.collection import SampleType
from lightly_studio.models.embedding_region import EmbeddingRegion, Point2D
from lightly_studio.resolvers import embedding_region_resolver, video_frame_resolver
from lightly_studio.resolvers.filter_with_collection_id import FilterWithCollectionId
from lightly_studio.resolvers.sample_resolver.sample_filter import SampleFilter
from lightly_studio.resolvers.video_frame_resolver import VideoFrameAdjacentFilter
from lightly_studio.resolvers.video_frame_resolver.video_frame_filter import VideoFrameFilter
from lightly_studio.resolvers.video_resolver.video_filter import VideoFilter
from tests import helpers_resolvers
from tests.resolvers.video import helpers as video_helpers


@pytest.mark.parametrize("region_video_indices", [[0, 2], [0], []])
def test_get_adjacent_video_frames__with_embedding_region(
    db_session: Session, mocker: MockerFixture, region_video_indices: list[int]
) -> None:
    collection = helpers_resolvers.create_collection(
        session=db_session, sample_type=SampleType.VIDEO
    )
    videos = [
        video_helpers.create_video_with_frames(
            session=db_session,
            collection_id=collection.collection_id,
            video=video_helpers.VideoStub(path=path, fps=1, duration_s=1.0),
        )
        for path in ["/videos/a.mp4", "/videos/b.mp4", "/videos/c.mp4"]
    ]
    mocker.patch.object(
        embedding_region_resolver,
        "get_sample_ids_in_region",
        return_value=[videos[index].video_sample_id for index in region_video_indices],
    )

    result = video_frame_resolver.get_adjacent_video_frames(
        session=db_session,
        sample_id=videos[0].frame_sample_ids[0],
        filters=VideoFrameAdjacentFilter(
            video_frame_filter=FilterWithCollectionId(
                collection_id=videos[0].video_frames_collection_id,
                filter=VideoFrameFilter(),
            ),
            video_filter=FilterWithCollectionId(
                collection_id=collection.collection_id,
                filter=VideoFilter(
                    sample_filter=SampleFilter(
                        embedding_region=EmbeddingRegion(
                            polygon=[Point2D(x=0, y=0), Point2D(x=1, y=0), Point2D(x=1, y=1)]
                        )
                    )
                ),
            ),
        ),
    )

    if not region_video_indices:
        assert result is None
        return
    assert result is not None
    assert result.sample_id == videos[0].frame_sample_ids[0]
    assert result.previous_sample_id is None
    assert result.next_sample_id == (
        videos[2].frame_sample_ids[0] if len(region_video_indices) == 2 else None
    )
    assert result.current_sample_position == 1
    assert result.total_count == len(region_video_indices)
