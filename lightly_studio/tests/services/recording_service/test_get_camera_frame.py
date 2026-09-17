"""Tests for reading a single camera frame from a recording."""

from __future__ import annotations

from collections import OrderedDict
from collections.abc import Iterator
from pathlib import Path
from typing import cast
from uuid import UUID, uuid4

import pytest
from pytest_mock import MockerFixture
from sqlmodel import Session

from lightly_studio.core.mcap import compressed_video
from lightly_studio.core.mcap.errors import ChannelNotFoundError
from lightly_studio.core.mcap.reader import McapFileReader
from lightly_studio.models.collection import CollectionCreate, CollectionTable, SampleType
from lightly_studio.models.recording import RecordingFormat
from lightly_studio.resolvers import collection_resolver, recording_resolver
from lightly_studio.services.recording_service import get_camera_frame
from lightly_studio.services.recording_service.get_camera_frame import (
    _READER_CACHE_SIZE,
    _get_cached_reader,
    _thread_local,
)
from tests.core.mcap import helpers


@pytest.fixture(autouse=True)
def clear_reader_cache() -> Iterator[None]:
    cache = cast(
        "OrderedDict[str, McapFileReader] | None",
        getattr(_thread_local, "reader_cache", None),
    )
    if cache is None:
        cache = OrderedDict()
        _thread_local.reader_cache = cache
    for reader in cache.values():
        reader.close()
    cache.clear()
    yield
    for reader in cache.values():
        reader.close()
    cache.clear()


def _create_recording(session: Session, collection: CollectionTable, mcap_path: Path) -> UUID:
    return recording_resolver.create(
        session=session,
        dataset_id=collection.dataset_id,
        uri=str(mcap_path),
        format_=RecordingFormat.MCAP,
    )


def _channel_id(mcap_path: Path) -> int:
    with McapFileReader(mcap_path) as reader:
        return next(
            topic.channel_id
            for topic in reader.get_topics()
            if topic.name == helpers.CAMERA_VIDEO_TOPIC
        )


def test_get_camera_frame(db_session: Session, tmp_path: Path, mocker: MockerFixture) -> None:
    mocker.patch.object(compressed_video, "from_decoded_message", return_value=b"\xff\xd8\xff")
    mcap_path = helpers.write_mcap(tmp_path / "recording.mcap")
    collection = collection_resolver.create(
        db_session, CollectionCreate(name="test_collection", sample_type=SampleType.IMAGE)
    )
    recording_id = _create_recording(db_session, collection, mcap_path)
    channel_id = _channel_id(mcap_path)
    keyframe_ns = helpers.VIDEO_KEYFRAME_LOG_TIMES_NS[0]

    frame = get_camera_frame(
        session=db_session,
        dataset_id=collection.dataset_id,
        recording_id=recording_id,
        channel_id=channel_id,
        keyframe_timestamp_ns=keyframe_ns,
    )

    assert frame is not None
    assert frame.media_type == "image/jpeg"
    assert frame.log_time_ns == keyframe_ns
    assert frame.data == b"\xff\xd8\xff"


def test_get_camera_frame__no_match(db_session: Session, tmp_path: Path) -> None:
    mcap_path = helpers.write_mcap(tmp_path / "recording.mcap")
    collection = collection_resolver.create(
        db_session, CollectionCreate(name="test_collection", sample_type=SampleType.IMAGE)
    )
    recording_id = _create_recording(db_session, collection, mcap_path)
    channel_id = _channel_id(mcap_path)

    frame = get_camera_frame(
        session=db_session,
        dataset_id=collection.dataset_id,
        recording_id=recording_id,
        channel_id=channel_id,
        keyframe_timestamp_ns=helpers.VIDEO_LOG_TIMES_NS[0] - 1,
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


def test_get_camera_frame__unknown_channel(db_session: Session, tmp_path: Path) -> None:
    mcap_path = helpers.write_mcap(tmp_path / "recording.mcap")
    collection = collection_resolver.create(
        db_session, CollectionCreate(name="test_collection", sample_type=SampleType.IMAGE)
    )
    recording_id = _create_recording(db_session, collection, mcap_path)

    with pytest.raises(ChannelNotFoundError):
        get_camera_frame(
            session=db_session,
            dataset_id=collection.dataset_id,
            recording_id=recording_id,
            channel_id=999_999,
            keyframe_timestamp_ns=helpers.VIDEO_KEYFRAME_LOG_TIMES_NS[0],
        )


def test_get_cached_reader__returns_same_reader_on_hit(tmp_path: Path) -> None:
    uri = str(helpers.write_mcap(tmp_path / "recording.mcap"))
    first = _get_cached_reader(uri)
    second = _get_cached_reader(uri)
    assert first is second


def test_get_cached_reader__evicts_lru_and_closes_it(tmp_path: Path) -> None:
    uris = [str(helpers.write_mcap(tmp_path / f"r{i}.mcap")) for i in range(_READER_CACHE_SIZE + 1)]
    evicted = _get_cached_reader(uris[0])
    for uri in uris[1:]:
        _get_cached_reader(uri)

    # The first reader was evicted; opening it again should yield a new object.
    replacement = _get_cached_reader(uris[0])
    assert evicted is not replacement


def test_get_cached_reader__local_uri_has_no_storage_options(tmp_path: Path) -> None:
    uri = str(helpers.write_mcap(tmp_path / "recording.mcap"))
    reader = _get_cached_reader(uri)
    # Local paths must not use blockcache — the fsspec open call would fail if it tried.
    assert reader is not None
