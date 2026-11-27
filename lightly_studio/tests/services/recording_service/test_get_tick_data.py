"""Tests for reading the sensor data of one tick."""

from __future__ import annotations

import io
import uuid
from collections.abc import Iterator
from pathlib import Path

import pytest
from PIL import Image
from pyarrow import ipc
from pytest_mock import MockerFixture
from sqlmodel import Session

from lightly_studio.core.mcap.reader import McapFileReader
from lightly_studio.services.recording_service import (
    get_camera_frame,
    get_tick_data,
    reader_cache,
    video_decoder_cache,
)
from lightly_studio.services.recording_service.get_tick_data import TickPayloadKind
from tests.core.mcap import helpers as mcap_helpers
from tests.services.recording_service import tick_data_helpers


@pytest.fixture(autouse=True)
def clear_caches() -> Iterator[None]:
    reader_cache.clear()
    video_decoder_cache.clear()
    yield
    reader_cache.clear()
    video_decoder_cache.clear()


def test_get_tick_data(db_session: Session, tmp_path: Path) -> None:
    tick = tick_data_helpers.create_tick(session=db_session, tmp_path=tmp_path)

    payloads = get_tick_data.get_tick_data(
        session=db_session,
        dataset_id=tick.dataset_id,
        sequence_id=tick.sequence_id,
        seq_number=0,
        camera_height=8,
    )

    assert payloads is not None
    point_cloud, camera = payloads
    assert (point_cloud.channel_id, point_cloud.kind, point_cloud.log_time_ns) == (
        tick.lidar_channel_id,
        TickPayloadKind.POINT_CLOUD,
        1_050_000_000,
    )
    with ipc.open_stream(io.BytesIO(point_cloud.data)) as stream:
        table = stream.read_all()
    assert table.column("x").to_pylist() == [1.0]
    assert table.schema.metadata[b"frame_id"] == mcap_helpers.LIDAR_FRAME_ID.encode()
    assert (camera.channel_id, camera.kind, camera.log_time_ns) == (
        tick.camera_channel_id,
        TickPayloadKind.CAMERA_JPEG,
        1_100_000_000,
    )
    # The frame at 1.1 s is the gray delta frame, decoded on top of the keyframe at 1.0 s.
    assert 96 < mcap_helpers.jpeg_mean_gray_level(camera.data) < 160
    assert Image.open(io.BytesIO(camera.data)).height == 8


def test_get_tick_data__unknown_tick(db_session: Session, tmp_path: Path) -> None:
    tick = tick_data_helpers.create_tick(session=db_session, tmp_path=tmp_path)

    assert (
        get_tick_data.get_tick_data(
            session=db_session,
            dataset_id=tick.dataset_id,
            sequence_id=tick.sequence_id,
            seq_number=1,
        )
        is None
    )
    assert (
        get_tick_data.get_tick_data(
            session=db_session, dataset_id=uuid.uuid4(), sequence_id=tick.sequence_id, seq_number=0
        )
        is None
    )


def test_get_tick_data__decodes_each_channel_in_its_window(
    db_session: Session, tmp_path: Path, mocker: MockerFixture
) -> None:
    tick = tick_data_helpers.create_tick(session=db_session, tmp_path=tmp_path)
    read_spy = mocker.spy(McapFileReader, "get_decoded_messages_in_windows")

    _get_tick(session=db_session, tick=tick)

    assert read_spy.call_args.kwargs["windows_ns"] == {
        tick.lidar_channel_id: (1_050_000_000, 1_050_000_000),
        tick.camera_channel_id: (1_000_000_000, 1_100_000_000),
    }


def test_get_tick_data__skips_a_cached_camera_jpeg(
    db_session: Session, tmp_path: Path, mocker: MockerFixture
) -> None:
    tick = tick_data_helpers.create_tick(session=db_session, tmp_path=tmp_path)
    first = _get_tick(session=db_session, tick=tick)
    read_spy = mocker.spy(McapFileReader, "get_decoded_messages_in_windows")

    second = _get_tick(session=db_session, tick=tick)

    assert read_spy.call_args.kwargs["windows_ns"] == {
        tick.lidar_channel_id: (1_050_000_000, 1_050_000_000),
    }
    assert second == first


def test_get_tick_data__continues_the_camera_decoder(
    db_session: Session, tmp_path: Path, mocker: MockerFixture
) -> None:
    tick = tick_data_helpers.create_tick(session=db_session, tmp_path=tmp_path)
    # Positions the decoder of the camera at the keyframe, as an earlier tick would.
    with McapFileReader(tmp_path / "recording.mcap") as reader:
        keyframe = reader.get_decoded_messages_in_range(
            channel_ids=[tick.camera_channel_id],
            start_time_ns=1_000_000_000,
            end_time_ns=1_000_000_000,
        )[tick.camera_channel_id]
    get_camera_frame.camera_jpeg(
        uri=str(tmp_path / "recording.mcap"),
        channel_id=tick.camera_channel_id,
        keyframe_log_time_ns=1_000_000_000,
        messages=keyframe,
        target_time_ns=1_000_000_000,
    )
    read_spy = mocker.spy(McapFileReader, "get_decoded_messages_in_windows")

    payloads = _get_tick(session=db_session, tick=tick)

    assert read_spy.call_args.kwargs["windows_ns"][tick.camera_channel_id] == (
        1_000_000_001,
        1_100_000_000,
    )
    assert 96 < mcap_helpers.jpeg_mean_gray_level(payloads[1].data) < 160


def test_get_tick_data__decoder_moved_on_reads_from_the_keyframe(
    db_session: Session, tmp_path: Path, mocker: MockerFixture
) -> None:
    tick = tick_data_helpers.create_tick(session=db_session, tmp_path=tmp_path)
    # The hint skips the keyframe, but the camera has no decoder to continue.
    mocker.patch.object(get_camera_frame, "camera_read_start_ns", return_value=1_100_000_000)
    fallback_spy = mocker.spy(get_camera_frame, "camera_jpeg_from_keyframe")

    payloads = _get_tick(session=db_session, tick=tick)

    fallback_spy.assert_called_once()
    assert [payload.kind for payload in payloads] == [
        TickPayloadKind.POINT_CLOUD,
        TickPayloadKind.CAMERA_JPEG,
    ]
    assert 96 < mcap_helpers.jpeg_mean_gray_level(payloads[1].data) < 160


def _get_tick(
    session: Session, tick: tick_data_helpers.TickFixture
) -> list[get_tick_data.TickPayload]:
    payloads = get_tick_data.get_tick_data(
        session=session, dataset_id=tick.dataset_id, sequence_id=tick.sequence_id, seq_number=0
    )
    assert payloads is not None
    return payloads
