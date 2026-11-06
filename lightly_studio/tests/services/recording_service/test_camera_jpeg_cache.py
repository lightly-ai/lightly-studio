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


def test_reserve() -> None:
    reserved = _jpeg_id(log_time_ns=100)
    other_size = _jpeg_id(log_time_ns=100, height=16)

    with camera_jpeg_cache.reserve(jpeg_ids=[reserved]):
        with camera_jpeg_cache.reserve(jpeg_ids=[reserved, other_size]):
            assert set(_reserved_at(log_time_ns=100)) == {reserved, other_size}
        assert _reserved_at(log_time_ns=100) == [reserved]
        assert _reserved_at(log_time_ns=200) == []

    assert _reserved_at(log_time_ns=100) == []


def test_reserve__released_on_error() -> None:
    with (
        pytest.raises(RuntimeError),
        camera_jpeg_cache.reserve(jpeg_ids=[_jpeg_id(log_time_ns=100)]),
    ):
        raise RuntimeError("request failed")

    assert _reserved_at(log_time_ns=100) == []


def _reserved_at(log_time_ns: int) -> list[JpegId]:
    return camera_jpeg_cache.reserved_at(uri="a.mcap", channel_id=1, log_time_ns=log_time_ns)


def _jpeg_id(log_time_ns: int, height: int = 8) -> JpegId:
    return JpegId(
        uri="a.mcap",
        channel_id=1,
        log_time_ns=log_time_ns,
        width=None,
        height=height,
        quality=85,
    )
