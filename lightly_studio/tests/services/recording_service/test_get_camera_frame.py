"""Tests for reading a single camera frame from a recording."""

from __future__ import annotations

from collections import OrderedDict
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path
from typing import cast
from uuid import UUID, uuid4

import pytest
from pytest_mock import MockerFixture, MockType
from sqlmodel import Session

from lightly_studio.core.mcap.compressed_video import VideoDecoder
from lightly_studio.core.mcap.errors import ChannelNotFoundError
from lightly_studio.core.mcap.reader import McapFileReader
from lightly_studio.models.collection import CollectionCreate, SampleType
from lightly_studio.models.recording import RecordingFormat
from lightly_studio.resolvers import collection_resolver, recording_resolver
from lightly_studio.services.recording_service import reader_cache, video_decoder_cache
from lightly_studio.services.recording_service.get_camera_frame import (
    CameraFrame,
    get_camera_frame,
)
from tests.core.mcap import helpers

# One GOP of real H.264 video: a black keyframe, then a gray and a white delta frame.
KEYFRAME_NS = 1_000_000_000
GRAY_FRAME_NS = 1_100_000_000
WHITE_FRAME_NS = 1_200_000_000
GRAY_LEVELS = (0, 128, 255)


@dataclass
class RecordingFixture:
    dataset_id: UUID
    recording_id: UUID
    channel_id: int


@pytest.fixture(autouse=True)
def clear_caches() -> Iterator[None]:
    cache = cast(
        "OrderedDict[str, McapFileReader] | None",
        getattr(reader_cache._thread_local, "reader_cache", None),
    )
    if cache is None:
        cache = OrderedDict()
        reader_cache._thread_local.reader_cache = cache
    for reader in cache.values():
        reader.close()
    cache.clear()
    video_decoder_cache.clear()
    yield
    for reader in cache.values():
        reader.close()
    cache.clear()
    video_decoder_cache.clear()


@pytest.fixture
def video_recording(db_session: Session, tmp_path: Path) -> RecordingFixture:
    access_units = helpers.h264_access_units(gray_levels=GRAY_LEVELS)
    mcap_path = helpers.write_mcap_with_video(
        tmp_path / "video.mcap",
        frames=list(zip((KEYFRAME_NS, GRAY_FRAME_NS, WHITE_FRAME_NS), access_units)),
    )
    return _create_recording(session=db_session, mcap_path=mcap_path)


def test_get_camera_frame(db_session: Session, video_recording: RecordingFixture) -> None:
    frame = get_camera_frame(
        session=db_session,
        dataset_id=video_recording.dataset_id,
        recording_id=video_recording.recording_id,
        channel_id=video_recording.channel_id,
        keyframe_timestamp_ns=KEYFRAME_NS,
    )

    assert frame is not None
    assert frame.media_type == "image/jpeg"
    assert frame.log_time_ns == KEYFRAME_NS
    assert helpers.jpeg_mean_gray_level(frame.data) < 32


def test_get_camera_frame__delta_frame(
    db_session: Session, video_recording: RecordingFixture
) -> None:
    frame = get_camera_frame(
        session=db_session,
        dataset_id=video_recording.dataset_id,
        recording_id=video_recording.recording_id,
        channel_id=video_recording.channel_id,
        keyframe_timestamp_ns=KEYFRAME_NS,
        log_time_ns=WHITE_FRAME_NS,
    )

    assert frame is not None
    assert frame.log_time_ns == WHITE_FRAME_NS
    assert helpers.jpeg_mean_gray_level(frame.data) > 223


def test_get_camera_frame__continues_cached_decoder(
    db_session: Session, video_recording: RecordingFixture, mocker: MockerFixture
) -> None:
    decode_spy = mocker.spy(VideoDecoder, "decode")

    gray_frame = _get_frame(
        session=db_session, recording=video_recording, log_time_ns=GRAY_FRAME_NS
    )
    gray_frame_decoded_ns = _decoded_log_times_ns(decode_spy=decode_spy)
    decode_spy.reset_mock()
    white_frame = _get_frame(
        session=db_session, recording=video_recording, log_time_ns=WHITE_FRAME_NS
    )

    assert gray_frame_decoded_ns == [KEYFRAME_NS, GRAY_FRAME_NS]
    assert _decoded_log_times_ns(decode_spy=decode_spy) == [WHITE_FRAME_NS]
    assert 96 < helpers.jpeg_mean_gray_level(gray_frame.data) < 160
    assert helpers.jpeg_mean_gray_level(white_frame.data) > 223


def test_get_camera_frame__same_frame_again(
    db_session: Session, video_recording: RecordingFixture, mocker: MockerFixture
) -> None:
    decode_spy = mocker.spy(VideoDecoder, "decode")

    first = _get_frame(session=db_session, recording=video_recording, log_time_ns=GRAY_FRAME_NS)
    decode_spy.reset_mock()
    second = _get_frame(session=db_session, recording=video_recording, log_time_ns=GRAY_FRAME_NS)

    assert _decoded_log_times_ns(decode_spy=decode_spy) == [KEYFRAME_NS, GRAY_FRAME_NS]
    assert second.data == first.data


def test_get_camera_frame__earlier_frame_restarts_at_keyframe(
    db_session: Session, video_recording: RecordingFixture, mocker: MockerFixture
) -> None:
    decode_spy = mocker.spy(VideoDecoder, "decode")

    _get_frame(session=db_session, recording=video_recording, log_time_ns=WHITE_FRAME_NS)
    decode_spy.reset_mock()
    gray_frame = _get_frame(
        session=db_session, recording=video_recording, log_time_ns=GRAY_FRAME_NS
    )

    assert _decoded_log_times_ns(decode_spy=decode_spy) == [KEYFRAME_NS, GRAY_FRAME_NS]
    assert 96 < helpers.jpeg_mean_gray_level(gray_frame.data) < 160


def test_get_camera_frame__log_time_before_keyframe(db_session: Session) -> None:
    with pytest.raises(ValueError, match="before the keyframe log time"):
        get_camera_frame(
            session=db_session,
            dataset_id=uuid4(),
            recording_id=uuid4(),
            channel_id=0,
            keyframe_timestamp_ns=1_000,
            log_time_ns=999,
        )


def test_get_camera_frame__no_match_at_log_time(
    db_session: Session, video_recording: RecordingFixture
) -> None:
    frame = get_camera_frame(
        session=db_session,
        dataset_id=video_recording.dataset_id,
        recording_id=video_recording.recording_id,
        channel_id=video_recording.channel_id,
        keyframe_timestamp_ns=KEYFRAME_NS,
        log_time_ns=GRAY_FRAME_NS + 1,
    )

    assert frame is None


def test_get_camera_frame__no_match(db_session: Session, video_recording: RecordingFixture) -> None:
    frame = get_camera_frame(
        session=db_session,
        dataset_id=video_recording.dataset_id,
        recording_id=video_recording.recording_id,
        channel_id=video_recording.channel_id,
        keyframe_timestamp_ns=KEYFRAME_NS - 1,
    )

    assert frame is None


def test_get_camera_frame__unknown_recording(db_session: Session) -> None:
    frame = get_camera_frame(
        session=db_session,
        dataset_id=uuid4(),
        recording_id=uuid4(),
        channel_id=0,
        keyframe_timestamp_ns=0,
    )
    assert frame is None


def test_get_camera_frame__unknown_channel(
    db_session: Session, video_recording: RecordingFixture
) -> None:
    with pytest.raises(ChannelNotFoundError):
        get_camera_frame(
            session=db_session,
            dataset_id=video_recording.dataset_id,
            recording_id=video_recording.recording_id,
            channel_id=999_999,
            keyframe_timestamp_ns=KEYFRAME_NS,
        )


def _create_recording(session: Session, mcap_path: Path) -> RecordingFixture:
    collection = collection_resolver.create(
        session, CollectionCreate(name="test_collection", sample_type=SampleType.IMAGE)
    )
    recording_id = recording_resolver.create(
        session=session,
        dataset_id=collection.dataset_id,
        uri=str(mcap_path),
        format_=RecordingFormat.MCAP,
    )
    with McapFileReader(mcap_path) as reader:
        channel_id = next(
            topic.channel_id
            for topic in reader.get_topics()
            if topic.name == helpers.CAMERA_VIDEO_TOPIC
        )
    return RecordingFixture(
        dataset_id=collection.dataset_id, recording_id=recording_id, channel_id=channel_id
    )


def _get_frame(session: Session, recording: RecordingFixture, log_time_ns: int) -> CameraFrame:
    frame = get_camera_frame(
        session=session,
        dataset_id=recording.dataset_id,
        recording_id=recording.recording_id,
        channel_id=recording.channel_id,
        keyframe_timestamp_ns=KEYFRAME_NS,
        log_time_ns=log_time_ns,
    )
    assert frame is not None
    return frame


def _decoded_log_times_ns(decode_spy: MockType) -> list[int]:
    return [call.kwargs["log_time_ns"] for call in decode_spy.call_args_list]
