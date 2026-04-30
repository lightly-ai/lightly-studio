from __future__ import annotations

from sqlmodel import Session

from lightly_studio.models.collection import SampleType
from lightly_studio.resolvers import video_frame_resolver
from lightly_studio.resolvers.video_frame_resolver.video_frame_filter import VideoFrameFilter
from tests.helpers_resolvers import create_collection
from tests.resolvers.video.helpers import VideoStub, create_video_with_frames


def test_get_sample_ids(db_session: Session) -> None:
    collection = create_collection(session=db_session, sample_type=SampleType.VIDEO)

    video_frames = create_video_with_frames(
        session=db_session,
        collection_id=collection.collection_id,
        video=VideoStub(path="/path/to/video.mp4", duration_s=2.0, fps=1),
    )

    all_sample_ids = video_frame_resolver.get_sample_ids(
        session=db_session,
        collection_id=video_frames.video_frames_collection_id,
    )
    assert all_sample_ids == set(video_frames.frame_sample_ids)


def test_get_sample_ids_with_video_id_filter(db_session: Session) -> None:
    collection = create_collection(session=db_session, sample_type=SampleType.VIDEO)

    video1 = create_video_with_frames(
        session=db_session,
        collection_id=collection.collection_id,
        video=VideoStub(path="/path/to/video1.mp4", duration_s=1.0, fps=1),
    )
    create_video_with_frames(
        session=db_session,
        collection_id=collection.collection_id,
        video=VideoStub(path="/path/to/video2.mp4", duration_s=1.0, fps=1),
    )

    filtered_ids = video_frame_resolver.get_sample_ids(
        session=db_session,
        collection_id=video1.video_frames_collection_id,
        filters=VideoFrameFilter(video_id=video1.video_sample_id),
    )
    assert filtered_ids == set(video1.frame_sample_ids)
