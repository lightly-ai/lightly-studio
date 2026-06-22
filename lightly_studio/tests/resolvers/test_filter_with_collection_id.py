"""Tests for FilterWithCollectionId."""

from __future__ import annotations

from uuid import uuid4

from sqlmodel import Session, select

from lightly_studio.models.collection import SampleType
from lightly_studio.models.video import VideoFrameTable
from lightly_studio.resolvers.filter_with_collection_id import FilterWithCollectionId
from lightly_studio.resolvers.image_filter import FilterDimensions
from lightly_studio.resolvers.video_frame_resolver.video_frame_filter import VideoFrameFilter
from tests import helpers_resolvers
from tests.resolvers.video import helpers as video_helpers


def test_apply__combines_collection_scope_and_inner_filter(db_session: Session) -> None:
    collection_a = helpers_resolvers.create_collection(
        session=db_session, collection_name="col_a", sample_type=SampleType.VIDEO
    )
    collection_b = helpers_resolvers.create_collection(
        session=db_session, collection_name="col_b", sample_type=SampleType.VIDEO
    )

    frames_a = video_helpers.create_video_with_frames(
        session=db_session,
        collection_id=collection_a.collection_id,
        video=video_helpers.VideoStub(path="/videos/a.mp4", fps=1, duration_s=3.0),
    )
    # Frames in another collection must be excluded by the collection scope.
    video_helpers.create_video_with_frames(
        session=db_session,
        collection_id=collection_b.collection_id,
        video=video_helpers.VideoStub(path="/videos/b.mp4", fps=1, duration_s=3.0),
    )

    query = select(VideoFrameTable).join(VideoFrameTable.sample)
    filtered = FilterWithCollectionId(
        collection_id=frames_a.video_frames_collection_id,
        filter=VideoFrameFilter(frame_number=FilterDimensions(min=2)),
    ).apply(query)
    result = db_session.exec(filtered).all()

    assert [row.sample_id for row in result] == [frames_a.frame_sample_ids[2]]


def test_apply__returns_empty_for_wrong_collection(db_session: Session) -> None:
    query = select(VideoFrameTable).join(VideoFrameTable.sample)
    filtered = FilterWithCollectionId(
        collection_id=uuid4(),
        filter=VideoFrameFilter(),
    ).apply(query)
    result = [row.sample_id for row in db_session.exec(filtered).all()]

    assert result == []
