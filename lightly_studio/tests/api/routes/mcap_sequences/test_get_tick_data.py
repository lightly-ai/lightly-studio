"""Tests for the tick data route."""

from __future__ import annotations

import struct
import uuid
from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session

from lightly_studio.api.routes.api.status import HTTP_STATUS_NOT_FOUND, HTTP_STATUS_OK
from lightly_studio.services.recording_service import reader_cache, video_decoder_cache
from tests.services.recording_service import tick_data_helpers


@pytest.fixture(autouse=True)
def clear_caches() -> Iterator[None]:
    reader_cache.clear()
    video_decoder_cache.clear()
    yield
    reader_cache.clear()
    video_decoder_cache.clear()


def test_get_tick_data(test_client: TestClient, db_session: Session, tmp_path: Path) -> None:
    tick = tick_data_helpers.create_tick(session=db_session, tmp_path=tmp_path)

    response = test_client.get(
        f"/datasets/{tick.dataset_id}/mcap-sequences/{tick.sequence_id}/ticks/0/data",
        params={"camera_height": 8},
    )

    assert response.status_code == HTTP_STATUS_OK
    assert response.headers["content-type"] == "application/octet-stream"
    payloads = _decode_payloads(body=response.content)
    assert [(channel_id, kind, log_time_ns) for channel_id, kind, log_time_ns, _ in payloads] == [
        (tick.lidar_channel_id, 0, 1_050_000_000),
        (tick.camera_channel_id, 1, 1_100_000_000),
    ]
    assert payloads[1][3][:3] == b"\xff\xd8\xff"  # JPEG magic


def test_get_tick_data__unknown_tick(test_client: TestClient) -> None:
    response = test_client.get(
        f"/datasets/{uuid.uuid4()}/mcap-sequences/{uuid.uuid4()}/ticks/0/data"
    )

    assert response.status_code == HTTP_STATUS_NOT_FOUND


def _decode_payloads(body: bytes) -> list[tuple[int, int, int, bytes]]:
    header = struct.Struct("<IBQQ")
    payloads = []
    offset = 0
    while offset < len(body):
        channel_id, kind, log_time_ns, length = header.unpack_from(body, offset)
        offset += header.size
        payloads.append((channel_id, kind, log_time_ns, body[offset : offset + length]))
        offset += length
    return payloads
