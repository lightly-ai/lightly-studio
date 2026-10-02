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

from lightly_studio.core.mcap.errors import McapAccessError, TransformNotFoundError
from lightly_studio.core.mcap.reader import McapFileReader
from lightly_studio.models.collection import CollectionCreate, SampleType
from lightly_studio.models.recording import RecordingFormat
from lightly_studio.models.static_transform import StaticTransformCreate
from lightly_studio.resolvers import (
    collection_resolver,
    recording_resolver,
    static_transform_resolver,
)
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
        {"recording_id": uuid4()},
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


def test_get_point_cloud__target_frame(
    db_session: Session, dataset_id: UUID, tmp_path: Path
) -> None:
    mcap_path = helpers.write_mcap(
        path=tmp_path / "with_tf.mcap",
        base_link_poses=[
            (1_000_000_000, (10.0, 0.0, 0.0)),
            (1_050_000_000, (20.0, 0.0, 0.0)),
        ],
    )
    recording_id = _create_recording(session=db_session, dataset_id=dataset_id, uri=mcap_path)
    # The lidar sits at (0, 1, 2) m in the base frame, without rotation.
    static_transform_resolver.create_many(
        session=db_session,
        rows=[
            StaticTransformCreate(
                recording_id=recording_id,
                parent="base_link",
                child=helpers.LIDAR_FRAME_ID,
                qx=0.0,
                qy=0.0,
                qz=0.0,
                qw=1.0,
                tx=0.0,
                ty=1.0,
                tz=2.0,
            )
        ],
    )

    point_cloud = get_point_cloud.get_point_cloud(
        session=db_session,
        dataset_id=dataset_id,
        recording_id=recording_id,
        channel_id=_channel_id(mcap_path=mcap_path, topic_name=helpers.LIDAR_POINTS_TOPIC),
        timestamp_ns=1_050_000_000,
        target_frame_id="map",
    )

    # The point (1, 2, 3) m in the lidar frame is (1, 3, 5) m in the base frame. The
    # base frame is at x = 20 m in the map at 1.05 s.
    assert point_cloud is not None
    table = _read_table(data=point_cloud.data)
    assert table.column("x").to_pylist() == [21.0]
    assert table.column("y").to_pylist() == [3.0]
    assert table.column("z").to_pylist() == [5.0]
    assert table.schema.metadata[b"frame_id"] == b"map"


def test_get_point_cloud__target_frame_at_capture_time(
    db_session: Session, dataset_id: UUID, tmp_path: Path
) -> None:
    # The lidar is captured at 1.0 s and logged at 1.05 s.
    mcap_path = helpers.write_mcap(
        path=tmp_path / "with_tf.mcap",
        lidar_stamp_offset_ns=-50_000_000,
        base_link_poses=[
            (1_000_000_000, (10.0, 0.0, 0.0)),
            (1_050_000_000, (20.0, 0.0, 0.0)),
        ],
    )
    recording_id = _create_recording(session=db_session, dataset_id=dataset_id, uri=mcap_path)
    static_transform_resolver.create_many(
        session=db_session,
        rows=[
            StaticTransformCreate(
                recording_id=recording_id,
                parent="base_link",
                child=helpers.LIDAR_FRAME_ID,
                qx=0.0,
                qy=0.0,
                qz=0.0,
                qw=1.0,
                tx=0.0,
                ty=0.0,
                tz=0.0,
            )
        ],
    )

    point_cloud = get_point_cloud.get_point_cloud(
        session=db_session,
        dataset_id=dataset_id,
        recording_id=recording_id,
        channel_id=_channel_id(mcap_path=mcap_path, topic_name=helpers.LIDAR_POINTS_TOPIC),
        timestamp_ns=1_050_000_000,
        target_frame_id="map",
    )

    # The base frame is at x = 10 m in the map at the capture time of 1.0 s.
    assert point_cloud is not None
    assert point_cloud.log_time_ns == 1_050_000_000
    table = _read_table(data=point_cloud.data)
    assert table.column("x").to_pylist() == [11.0]


def test_get_point_cloud__target_frame_is_sensor_frame(
    db_session: Session, dataset_id: UUID, recording_id: UUID, channel_id: int
) -> None:
    point_cloud = get_point_cloud.get_point_cloud(
        session=db_session,
        dataset_id=dataset_id,
        recording_id=recording_id,
        channel_id=channel_id,
        timestamp_ns=helpers.LIDAR_LOG_TIMES_NS[0],
        target_frame_id=helpers.LIDAR_FRAME_ID,
    )

    assert point_cloud is not None
    table = _read_table(data=point_cloud.data)
    assert table.column("x").to_pylist() == [1.0]
    assert table.column("y").to_pylist() == [2.0]
    assert table.column("z").to_pylist() == [3.0]
    assert table.schema.metadata[b"frame_id"] == helpers.LIDAR_FRAME_ID.encode()


def test_get_point_cloud__target_frame_not_connected(
    db_session: Session, dataset_id: UUID, recording_id: UUID, channel_id: int
) -> None:
    # No static transforms are stored and the recording has no `/tf` topic.
    with pytest.raises(TransformNotFoundError):
        get_point_cloud.get_point_cloud(
            session=db_session,
            dataset_id=dataset_id,
            recording_id=recording_id,
            channel_id=channel_id,
            timestamp_ns=helpers.LIDAR_LOG_TIMES_NS[0],
            target_frame_id="map",
        )


def _create_recording(session: Session, dataset_id: UUID, uri: Path) -> UUID:
    return recording_resolver.create(
        session=session, dataset_id=dataset_id, uri=str(uri), format_=RecordingFormat.MCAP
    )


def _channel_id(mcap_path: Path, topic_name: str) -> int:
    with McapFileReader(mcap_path) as reader:
        return next(topic.channel_id for topic in reader.get_topics() if topic.name == topic_name)


def _read_table(data: bytes) -> pa.Table:
    with ipc.open_stream(io.BytesIO(data)) as stream:
        return stream.read_all()
