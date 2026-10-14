"""Tests for the process-wide video decoder cache."""

from __future__ import annotations

import threading
from collections.abc import Iterator

import pytest
from pytest_mock import MockerFixture

from lightly_studio.services.recording_service import camera_jpeg_cache, video_decoder_cache
from lightly_studio.services.recording_service.camera_jpeg_cache import JpegId


@pytest.fixture(autouse=True)
def clear_decoder_cache() -> Iterator[None]:
    video_decoder_cache.clear()
    yield
    video_decoder_cache.clear()


def test_borrow_decoder__starts_without_a_decoder() -> None:
    with video_decoder_cache.borrow_decoder(uri="a.mcap", channel_id=1) as lease:
        assert lease.decoder is None


def test_borrow_decoder__drops_a_decoder_that_was_not_fed() -> None:
    with video_decoder_cache.borrow_decoder(uri="a.mcap", channel_id=1) as lease:
        lease.reset(keyframe_log_time_ns=100)

    with video_decoder_cache.borrow_decoder(uri="a.mcap", channel_id=1) as lease:
        assert lease.decoder is None


def test_borrow_decoder__locks_per_channel() -> None:
    entered = threading.Event()

    def other() -> None:
        with video_decoder_cache.borrow_decoder(uri="b.mcap", channel_id=1):
            entered.set()

    with video_decoder_cache.borrow_decoder(uri="a.mcap", channel_id=1):
        thread = threading.Thread(target=other, daemon=True)
        thread.start()
        assert entered.wait(timeout=2)
    thread.join(timeout=2)


def test_borrow_decoder__waits_for_the_channel() -> None:
    started = threading.Event()
    release = threading.Event()
    finished = threading.Event()

    def hold() -> None:
        with video_decoder_cache.borrow_decoder(uri="a.mcap", channel_id=1):
            started.set()
            assert release.wait(timeout=5)

    def wait_for_holder() -> None:
        assert started.wait(timeout=5)
        with video_decoder_cache.borrow_decoder(uri="a.mcap", channel_id=1):
            finished.set()

    holder = threading.Thread(target=hold)
    waiter = threading.Thread(target=wait_for_holder)
    holder.start()
    assert started.wait(timeout=5)
    waiter.start()
    assert not finished.wait(timeout=0.2)
    release.set()
    assert finished.wait(timeout=5)
    holder.join(timeout=5)
    waiter.join(timeout=5)
    assert not holder.is_alive()
    assert not waiter.is_alive()


def test_borrow_decoder__evicts_the_least_recently_used(mocker: MockerFixture) -> None:
    mocker.patch.object(video_decoder_cache, "_DECODER_CACHE_SIZE", 2)

    for channel_id in (0, 1, 2):
        with video_decoder_cache.borrow_decoder(uri="a.mcap", channel_id=channel_id):
            pass

    assert list(video_decoder_cache._channels) == [("a.mcap", 1), ("a.mcap", 2)]


def test_borrow_decoder__keeps_a_decoder_that_is_in_use(mocker: MockerFixture) -> None:
    mocker.patch.object(video_decoder_cache, "_DECODER_CACHE_SIZE", 1)

    with video_decoder_cache.borrow_decoder(uri="a.mcap", channel_id=0):
        with video_decoder_cache.borrow_decoder(uri="a.mcap", channel_id=1):
            pass
        with video_decoder_cache.borrow_decoder(uri="a.mcap", channel_id=2):
            assert ("a.mcap", 0) in video_decoder_cache._channels
            assert ("a.mcap", 1) not in video_decoder_cache._channels


def test_clear() -> None:
    with video_decoder_cache.borrow_decoder(uri="a.mcap", channel_id=1) as lease:
        lease.reset(keyframe_log_time_ns=100)
    jpeg_id = JpegId(uri="a.mcap", channel_id=1, log_time_ns=100, width=None, height=8, quality=85)
    camera_jpeg_cache.put_jpeg(jpeg_id=jpeg_id, data=b"jpeg")

    video_decoder_cache.clear()

    with video_decoder_cache.borrow_decoder(uri="a.mcap", channel_id=1) as lease:
        assert lease.decoder is None
    assert camera_jpeg_cache.get_jpeg(jpeg_id=jpeg_id) is None
