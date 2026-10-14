"""Tests for reading the sensor data of one tick."""

from __future__ import annotations

import io
import uuid
from collections.abc import Iterator
from pathlib import Path

import pytest
from PIL import Image
from pyarrow import ipc
from sqlmodel import Session

from lightly_studio.services.recording_service import (
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
