from __future__ import annotations

import pytest
from sqlmodel import Session

from lightly_studio.models.collection import SampleType
from lightly_studio.resolvers import video_resolver
from tests.helpers_resolvers import create_collection
from tests.resolvers.video.helpers import VideoStub, create_video


def test_get_sample_ids_by_stems(db_session: Session) -> None:
    collection = create_collection(session=db_session, sample_type=SampleType.VIDEO)
    other_collection = create_collection(session=db_session, sample_type=SampleType.VIDEO)

    video = create_video(
        session=db_session,
        collection_id=collection.collection_id,
        video=VideoStub(path="/data/videos/v_action1.mp4"),
    )
    create_video(
        session=db_session,
        collection_id=other_collection.collection_id,
        video=VideoStub(path="/data/videos/v_other.mp4"),
    )

    stem_to_sample_id = video_resolver.get_sample_ids_by_stems(
        session=db_session,
        collection_id=collection.collection_id,
    )

    # Only videos of the requested collection are returned, indexed by stem.
    assert stem_to_sample_id == {"v_action1": video.sample_id}


def test_get_sample_ids_by_stems__raises_on_duplicate_stem(db_session: Session) -> None:
    collection = create_collection(session=db_session, sample_type=SampleType.VIDEO)

    # Two videos with different paths but the same file name stem.
    create_video(
        session=db_session,
        collection_id=collection.collection_id,
        video=VideoStub(path="/data/a/v_action1.mp4"),
    )
    create_video(
        session=db_session,
        collection_id=collection.collection_id,
        video=VideoStub(path="/data/b/v_action1.mp4"),
    )

    with pytest.raises(ValueError, match="Duplicate video stem 'v_action1'"):
        video_resolver.get_sample_ids_by_stems(
            session=db_session,
            collection_id=collection.collection_id,
        )
