"""Tests for the process-wide camera JPEG cache."""

from __future__ import annotations

from collections.abc import Iterator

import pytest
from pytest_mock import MockerFixture

from lightly_studio.services.recording_service import camera_jpeg_cache
from lightly_studio.services.recording_service.camera_jpeg_cache import JpegId


@pytest.fixture(autouse=True)
def clear_jpeg_cache() -> Iterator[None]:
    camera_jpeg_cache.clear()
    yield
    camera_jpeg_cache.clear()


def test_get_jpeg__miss() -> None:
    assert camera_jpeg_cache.get_jpeg(jpeg_id=_jpeg_id(log_time_ns=100)) is None


def test_put_jpeg__returns_the_stored_bytes() -> None:
    camera_jpeg_cache.put_jpeg(jpeg_id=_jpeg_id(log_time_ns=100), data=b"jpeg")

    assert camera_jpeg_cache.get_jpeg(jpeg_id=_jpeg_id(log_time_ns=100)) == b"jpeg"
    assert camera_jpeg_cache.get_jpeg(jpeg_id=_jpeg_id(log_time_ns=100, height=16)) is None


def test_put_jpeg__evicts_the_least_recently_used(mocker: MockerFixture) -> None:
    mocker.patch.object(camera_jpeg_cache, "_JPEG_CACHE_SIZE", 2)
    for log_time_ns in (100, 200, 300):
        camera_jpeg_cache.put_jpeg(
            jpeg_id=_jpeg_id(log_time_ns=log_time_ns), data=str(log_time_ns).encode()
        )

    assert camera_jpeg_cache.get_jpeg(jpeg_id=_jpeg_id(log_time_ns=100)) is None
    assert camera_jpeg_cache.get_jpeg(jpeg_id=_jpeg_id(log_time_ns=300)) == b"300"


def _jpeg_id(log_time_ns: int, height: int = 8) -> JpegId:
    return JpegId(
        uri="a.mcap",
        channel_id=1,
        log_time_ns=log_time_ns,
        width=None,
        height=height,
        quality=85,
    )
