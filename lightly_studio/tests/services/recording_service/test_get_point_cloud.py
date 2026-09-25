"""Tests for reading a single point-cloud message from a recording."""

from __future__ import annotations

import io
from collections import OrderedDict
from collections.abc import Iterator
from pathlib import Path
from typing import cast
from uuid import UUID, uuid4

import pyarrow as pa
import pytest
from pyarrow import ipc
from sqlmodel import Session

from lightly_studio.core.mcap.errors import ChannelNotFoundError, McapAccessError
from lightly_studio.core.mcap.reader import McapFileReader
from lightly_studio.models.collection import CollectionCreate, SampleType
from lightly_studio.models.recording import RecordingFormat
from lightly_studio.resolvers import collection_resolver, recording_resolver
from lightly_studio.services.recording_service import get_point_cloud, reader_cache
from tests.core.mcap import helpers


@pytest.fixture(autouse=True)
def clear_reader_cache() -> Iterator[None]:
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
    yield
    for reader in cache.values():
        reader.close()
    cache.clear()


@pytest.fixture
def mcap_path(tmp_path: Path) -> Path:
    return helpers.write_mcap(path=tmp_path / "recording.mcap")


@pytest.fixture
def dataset_id(db_session: Session) -> UUID:
    collection = collection_resolver.create(
        db_session, CollectionCreate(name="test_collection", sample_type=SampleType.IMAGE)
    )
    return collection.dataset_id


@pytest.fixture
def recording_id(db_session: Session, dataset_id: UUID, mcap_path: Path) -> UUID:
    return recording_resolver.create(
        session=db_session,
        dataset_id=dataset_id,
        uri=str(mcap_path),
        format_=RecordingFormat.MCAP,
    )


@pytest.fixture
def channel_id(mcap_path: Path) -> int:
    return _channel_id(mcap_path=mcap_path, topic_name=helpers.LIDAR_POINTS_TOPIC)


def test_get_point_cloud(
    db_session: Session, dataset_id: UUID, recording_id: UUID, channel_id: int
) -> None:
    timestamp_ns = helpers.LIDAR_LOG_TIMES_NS[0]

    point_cloud = get_point_cloud.get_point_cloud(
        session=db_session,
        dataset_id=dataset_id,
        recording_id=recording_id,
        channel_id=channel_id,
        timestamp_ns=timestamp_ns,
    )

    assert point_cloud is not None
    assert point_cloud.log_time_ns == timestamp_ns
    table = _read_table(data=point_cloud.data)
    assert table.column("x").to_pylist() == [1.0]
    assert table.column("y").to_pylist() == [2.0]
    assert table.column("z").to_pylist() == [3.0]
    metadata = table.schema.metadata
    assert metadata[b"frame_id"] == helpers.LIDAR_FRAME_ID.encode()
    assert metadata[b"topic"] == helpers.LIDAR_POINTS_TOPIC.encode()
    assert metadata[b"source_point_count"] == b"1"
    assert metadata[b"point_count"] == b"1"
    assert metadata[b"coordinate_unit"] == b"meter"


@pytest.mark.parametrize(
    "overrides",
    [
        {"timestamp_ns": helpers.LIDAR_LOG_TIMES_NS[0] - 1},
        {"dataset_id": uuid4()},
    ],
)
def test_get_point_cloud__no_result(
    db_session: Session,
    dataset_id: UUID,
    recording_id: UUID,
    channel_id: int,
    overrides: dict[str, object],
) -> None:
    kwargs: dict[str, object] = {
        "session": db_session,
        "dataset_id": dataset_id,
        "recording_id": recording_id,
        "channel_id": channel_id,
        "timestamp_ns": helpers.LIDAR_LOG_TIMES_NS[0],
    }
    kwargs.update(overrides)

    assert get_point_cloud.get_point_cloud(**kwargs) is None  # type: ignore[arg-type]


def test_get_point_cloud__unknown_recording(db_session: Session) -> None:
    point_cloud = get_point_cloud.get_point_cloud(
        session=db_session,
        dataset_id=uuid4(),
        recording_id=uuid4(),
        channel_id=0,
        timestamp_ns=0,
    )

    assert point_cloud is None


def test_get_point_cloud__unknown_channel(
    db_session: Session, dataset_id: UUID, recording_id: UUID
) -> None:
    with pytest.raises(ChannelNotFoundError):
        get_point_cloud.get_point_cloud(
            session=db_session,
            dataset_id=dataset_id,
            recording_id=recording_id,
            channel_id=999_999,
            timestamp_ns=helpers.LIDAR_LOG_TIMES_NS[0],
        )


def test_get_point_cloud__non_point_cloud_channel(
    db_session: Session, dataset_id: UUID, recording_id: UUID, mcap_path: Path
) -> None:
    channel_id = _channel_id(mcap_path=mcap_path, topic_name=helpers.CAMERA_VIDEO_TOPIC)

    with pytest.raises(McapAccessError):
        get_point_cloud.get_point_cloud(
            session=db_session,
            dataset_id=dataset_id,
            recording_id=recording_id,
            channel_id=channel_id,
            timestamp_ns=helpers.VIDEO_LOG_TIMES_NS[0],
        )


def _channel_id(mcap_path: Path, topic_name: str) -> int:
    with McapFileReader(mcap_path) as reader:
        return next(topic.channel_id for topic in reader.get_topics() if topic.name == topic_name)


def _read_table(data: bytes) -> pa.Table:
    with ipc.open_stream(io.BytesIO(data)) as stream:
        return stream.read_all()
