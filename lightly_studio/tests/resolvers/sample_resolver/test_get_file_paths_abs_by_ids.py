from __future__ import annotations

import pytest
from sqlmodel import Session

from lightly_studio.models.collection import SampleType
from lightly_studio.resolvers import sample_resolver
from tests.helpers_resolvers import create_collection, create_image
from tests.resolvers.video.helpers import VideoStub, create_video, create_video_with_frames


def test_get_file_paths_abs_by_ids__images(db_session: Session) -> None:
    collection = create_collection(session=db_session, sample_type=SampleType.IMAGE)
    image_a = create_image(
        session=db_session, collection_id=collection.collection_id, file_path_abs="/a.png"
    )
    image_b = create_image(
        session=db_session, collection_id=collection.collection_id, file_path_abs="/b.png"
    )

    file_paths_abs = sample_resolver.get_file_paths_abs_by_ids(
        session=db_session,
        collection_id=collection.collection_id,
        sample_ids=[image_a.sample_id, image_b.sample_id],
    )

    assert file_paths_abs == {image_a.sample_id: "/a.png", image_b.sample_id: "/b.png"}


def test_get_file_paths_abs_by_ids__videos(db_session: Session) -> None:
    collection = create_collection(session=db_session, sample_type=SampleType.VIDEO)
    video = create_video(
        session=db_session,
        collection_id=collection.collection_id,
        video=VideoStub(path="/video.mp4"),
    )

    file_paths_abs = sample_resolver.get_file_paths_abs_by_ids(
        session=db_session,
        collection_id=collection.collection_id,
        sample_ids=[video.sample_id],
    )

    assert file_paths_abs == {video.sample_id: "/video.mp4"}


def test_get_file_paths_abs_by_ids__video_frames(db_session: Session) -> None:
    """Frames resolve to the absolute path of their parent video."""
    collection = create_collection(session=db_session, sample_type=SampleType.VIDEO)
    video_with_frames = create_video_with_frames(
        session=db_session,
        collection_id=collection.collection_id,
        video=VideoStub(path="/video.mp4", duration_s=0.1, fps=30.0),
    )
    frame_sample_ids = video_with_frames.frame_sample_ids

    file_paths_abs = sample_resolver.get_file_paths_abs_by_ids(
        session=db_session,
        collection_id=video_with_frames.video_frames_collection_id,
        sample_ids=frame_sample_ids,
    )

    assert file_paths_abs == dict.fromkeys(frame_sample_ids, "/video.mp4")


def test_get_file_paths_abs_by_ids__unknown_sample_ids_are_omitted(db_session: Session) -> None:
    collection = create_collection(session=db_session, sample_type=SampleType.IMAGE)
    image = create_image(
        session=db_session, collection_id=collection.collection_id, file_path_abs="/a.png"
    )
    other_collection = create_collection(session=db_session, sample_type=SampleType.IMAGE)
    other_image = create_image(
        session=db_session, collection_id=other_collection.collection_id, file_path_abs="/b.png"
    )

    file_paths_abs = sample_resolver.get_file_paths_abs_by_ids(
        session=db_session,
        collection_id=collection.collection_id,
        sample_ids=[image.sample_id],
    )

    assert file_paths_abs == {image.sample_id: "/a.png"}
    assert other_image.sample_id not in file_paths_abs


def test_get_file_paths_abs_by_ids__unsupported_sample_type(db_session: Session) -> None:
    """Sample types without a file path yield an empty mapping instead of raising."""
    collection = create_collection(session=db_session, sample_type=SampleType.GROUP)

    file_paths_abs = sample_resolver.get_file_paths_abs_by_ids(
        session=db_session,
        collection_id=collection.collection_id,
        sample_ids=[],
    )

    assert file_paths_abs == {}


def test_get_file_paths_abs_by_ids__missing_collection(db_session: Session) -> None:
    collection = create_collection(session=db_session, sample_type=SampleType.IMAGE)
    image = create_image(
        session=db_session, collection_id=collection.collection_id, file_path_abs="/a.png"
    )

    with pytest.raises(ValueError, match="not found"):
        sample_resolver.get_file_paths_abs_by_ids(
            session=db_session,
            collection_id=image.sample_id,
            sample_ids=[image.sample_id],
        )
