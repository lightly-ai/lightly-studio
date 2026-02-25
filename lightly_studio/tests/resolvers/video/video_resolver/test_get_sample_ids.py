from __future__ import annotations

import pytest
from sqlmodel import Session

from lightly_studio.models.collection import SampleType
from lightly_studio.resolvers import video_resolver
from lightly_studio.resolvers.image_filter import FilterDimensions
from lightly_studio.resolvers.sample_resolver.sample_filter import SampleFilter
from lightly_studio.resolvers.video_resolver.video_filter import VideoFilter
from tests.helpers_resolvers import create_collection
from tests.resolvers.video.helpers import VideoStub, create_videos


def test_get_sample_ids(test_db: Session) -> None:
    collection = create_collection(session=test_db, sample_type=SampleType.VIDEO)
    other_collection = create_collection(session=test_db, sample_type=SampleType.VIDEO)

    created_video_ids = create_videos(
        session=test_db,
        collection_id=collection.collection_id,
        videos=[
            VideoStub(path="/path/to/small.mp4", width=100, height=100),
            VideoStub(path="/path/to/large.mp4", width=800, height=800),
        ],
    )
    create_videos(
        session=test_db,
        collection_id=other_collection.collection_id,
        videos=[VideoStub(path="/path/to/other.mp4", width=800, height=800)],
    )

    all_sample_ids = video_resolver.get_sample_ids(
        session=test_db,
        filters=VideoFilter(sample_filter=SampleFilter(collection_id=collection.collection_id)),
    )
    assert all_sample_ids == set(created_video_ids)

    filtered_sample_ids = video_resolver.get_sample_ids(
        session=test_db,
        filters=VideoFilter(
            sample_filter=SampleFilter(collection_id=collection.collection_id),
            width=FilterDimensions(min=500),
        ),
    )
    assert filtered_sample_ids == {created_video_ids[1]}


def test_get_sample_ids__no_collection_id(test_db: Session) -> None:
    with pytest.raises(ValueError, match="Collection ID must be provided in the sample filter."):
        video_resolver.get_sample_ids(
            session=test_db,
            filters=VideoFilter(width=FilterDimensions(min=500)),
        )
