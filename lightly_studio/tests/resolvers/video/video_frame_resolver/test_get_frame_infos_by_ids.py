from uuid import uuid4

from sqlmodel import Session

from lightly_studio.models.collection import SampleType
from lightly_studio.resolvers import video_frame_resolver
from lightly_studio.utils import batching
from tests.helpers_resolvers import create_collection
from tests.resolvers.video.helpers import VideoStub, create_video_with_frames


def test_get_frame_infos_by_ids__preserves_input_sample_id_order(db_session: Session) -> None:
    collection = create_collection(session=db_session, sample_type=SampleType.VIDEO)
    video_a = create_video_with_frames(
        session=db_session,
        collection_id=collection.collection_id,
        video=VideoStub(path="/data/a.mp4", duration_s=2.0, fps=1.0),
    )
    video_b = create_video_with_frames(
        session=db_session,
        collection_id=collection.collection_id,
        video=VideoStub(path="/data/b.mp4", duration_s=2.0, fps=1.0),
    )
    # Reverse of insertion order so SQL IN cannot accidentally match.
    input_sample_ids = list(video_b.frame_sample_ids) + list(video_a.frame_sample_ids)

    frames = video_frame_resolver.get_frame_infos_by_ids(
        session=db_session, sample_ids=input_sample_ids
    )

    assert [frame.sample_id for frame in frames] == input_sample_ids


def test_get_frame_infos_by_ids__returns_parent_and_frame_number(db_session: Session) -> None:
    collection = create_collection(session=db_session, sample_type=SampleType.VIDEO)
    video = create_video_with_frames(
        session=db_session,
        collection_id=collection.collection_id,
        video=VideoStub(path="/data/a.mp4", duration_s=3.0, fps=1.0),
    )

    frames = video_frame_resolver.get_frame_infos_by_ids(
        session=db_session, sample_ids=video.frame_sample_ids
    )

    assert [frame.frame_number for frame in frames] == [0, 1, 2]
    assert {frame.parent_sample_id for frame in frames} == {video.video_sample_id}


def test_get_frame_infos_by_ids__omits_missing_ids(db_session: Session) -> None:
    collection = create_collection(session=db_session, sample_type=SampleType.VIDEO)
    video = create_video_with_frames(
        session=db_session,
        collection_id=collection.collection_id,
        video=VideoStub(path="/data/a.mp4", duration_s=2.0, fps=1.0),
    )

    frames = video_frame_resolver.get_frame_infos_by_ids(
        session=db_session,
        sample_ids=[uuid4(), video.frame_sample_ids[0], uuid4()],
    )

    assert [frame.sample_id for frame in frames] == [video.frame_sample_ids[0]]


def test_get_frame_infos_by_ids__empty(db_session: Session) -> None:
    assert video_frame_resolver.get_frame_infos_by_ids(session=db_session, sample_ids=[]) == []


def test_get_frame_infos_by_ids__spans_multiple_batches(db_session: Session) -> None:
    """More ids than one batch holds, so the results must be merged across batches."""
    collection = create_collection(session=db_session, sample_type=SampleType.VIDEO)
    video = create_video_with_frames(
        session=db_session,
        collection_id=collection.collection_id,
        video=VideoStub(path="/data/a.mp4", duration_s=1.0, fps=1.0),
    )
    # The only matching id goes last, so it lands in a batch after the first one.
    sample_ids = [uuid4() for _ in range(batching.DEFAULT_BATCH_SIZE)]
    sample_ids.append(video.frame_sample_ids[0])

    frames = video_frame_resolver.get_frame_infos_by_ids(session=db_session, sample_ids=sample_ids)

    assert [frame.sample_id for frame in frames] == [video.frame_sample_ids[0]]
