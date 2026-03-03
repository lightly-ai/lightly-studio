from uuid import uuid4

from sqlmodel import Session

from lightly_studio.models.collection import SampleType
from lightly_studio.resolvers import (
    video_frame_resolver,
)
from tests.helpers_resolvers import (
    create_collection,
)
from tests.resolvers.video.helpers import VideoStub, create_video_with_frames


def test_get_all_by_video_id(test_db: Session) -> None:
    collection = create_collection(session=test_db, sample_type=SampleType.VIDEO)

    # Create video frames for two videos.
    video_frames = create_video_with_frames(
        session=test_db,
        collection_id=collection.collection_id,
        video=VideoStub(path="video1.mp4", duration_s=1, fps=2),
    )

    create_video_with_frames(
        session=test_db,
        collection_id=collection.collection_id,
        video=VideoStub(path="video2.mp4", duration_s=1, fps=2),
    )
    # Retrieve frames for the first video.
    result = video_frame_resolver.get_all_by_video_ids(
        session=test_db,
        video_ids=[video_frames.video_sample_id],
    )
    assert len(result) == 2
    assert result[0].sample_id == video_frames.frame_sample_ids[0]
    assert result[1].sample_id == video_frames.frame_sample_ids[1]


def test_get_all_by_video_id__video_id_not_found(test_db: Session) -> None:
    collection = create_collection(session=test_db, sample_type=SampleType.VIDEO)

    # Create video frames for two videos.
    create_video_with_frames(
        session=test_db,
        collection_id=collection.collection_id,
        video=VideoStub(path="video1.mp4", duration_s=1, fps=2),
    )
    # Try to retrieve frames for a non-existent video ID.
    result = video_frame_resolver.get_all_by_video_ids(
        session=test_db,
        video_ids=[uuid4()],
    )
    assert len(result) == 0
