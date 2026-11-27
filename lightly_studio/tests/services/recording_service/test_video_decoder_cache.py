"""Tests for the process-wide video decoder cache."""

from __future__ import annotations

import threading
import time
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
    with video_decoder_cache.borrow_decoder(
        uri="a.mcap", channel_id=1, keyframe_log_time_ns=100
    ) as lease:
        assert lease.decoder is None


def test_borrow_decoder__reset_starts_at_the_keyframe() -> None:
    with video_decoder_cache.borrow_decoder(
        uri="a.mcap", channel_id=1, keyframe_log_time_ns=100
    ) as lease:
        assert lease.reset().keyframe_log_time_ns == 100


def test_borrow_decoder__drops_a_decoder_that_was_not_fed() -> None:
    with video_decoder_cache.borrow_decoder(
        uri="a.mcap", channel_id=1, keyframe_log_time_ns=100
    ) as lease:
        lease.reset()

    with video_decoder_cache.borrow_decoder(
        uri="a.mcap", channel_id=1, keyframe_log_time_ns=100
    ) as lease:
        assert lease.decoder is None


def test_borrow_decoder__keeps_one_decoder_per_gop() -> None:
    with video_decoder_cache.borrow_decoder(
        uri="a.mcap", channel_id=1, keyframe_log_time_ns=100
    ) as lease:
        first = lease.reset()
        first.last_log_time_ns = 100
    with video_decoder_cache.borrow_decoder(
        uri="a.mcap", channel_id=1, keyframe_log_time_ns=200
    ) as lease:
        second = lease.reset()
        second.last_log_time_ns = 200

    assert (
        video_decoder_cache.peek_decoder(uri="a.mcap", channel_id=1, keyframe_log_time_ns=100)
        is first
    )
    assert (
        video_decoder_cache.peek_decoder(uri="a.mcap", channel_id=1, keyframe_log_time_ns=200)
        is second
    )


def test_borrow_decoder__locks_per_gop() -> None:
    entered = threading.Event()

    def other() -> None:
        with video_decoder_cache.borrow_decoder(
            uri="a.mcap", channel_id=1, keyframe_log_time_ns=200
        ):
            entered.set()

    with video_decoder_cache.borrow_decoder(uri="a.mcap", channel_id=1, keyframe_log_time_ns=100):
        thread = threading.Thread(target=other, daemon=True)
        thread.start()
        assert entered.wait(timeout=2)
    thread.join(timeout=2)


def test_borrow_decoder__waits_for_the_gop() -> None:
    started = threading.Event()
    release = threading.Event()
    finished = threading.Event()

    def hold() -> None:
        with video_decoder_cache.borrow_decoder(
            uri="a.mcap", channel_id=1, keyframe_log_time_ns=100
        ):
            started.set()
            assert release.wait(timeout=5)

    def wait_for_holder() -> None:
        assert started.wait(timeout=5)
        with video_decoder_cache.borrow_decoder(
            uri="a.mcap", channel_id=1, keyframe_log_time_ns=100
        ):
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


def test_borrow_decoder__a_waiting_request_does_not_block_other_gops() -> None:
    release = threading.Event()
    holding = threading.Event()
    other_gop_entered = threading.Event()

    def hold() -> None:
        with video_decoder_cache.borrow_decoder(
            uri="a.mcap", channel_id=1, keyframe_log_time_ns=100
        ):
            holding.set()
            assert release.wait(timeout=5)

    def wait_for_holder() -> None:
        with video_decoder_cache.borrow_decoder(
            uri="a.mcap", channel_id=1, keyframe_log_time_ns=100
        ):
            pass

    def borrow_other_gop() -> None:
        with video_decoder_cache.borrow_decoder(
            uri="a.mcap", channel_id=2, keyframe_log_time_ns=100
        ):
            other_gop_entered.set()

    holder = threading.Thread(target=hold)
    waiter = threading.Thread(target=wait_for_holder)
    other = threading.Thread(target=borrow_other_gop)
    holder.start()
    try:
        assert holding.wait(timeout=5)
        waiter.start()
        assert _users(key=("a.mcap", 1, 100)) == 2, "The second request did not wait."
        other.start()
        assert other_gop_entered.wait(timeout=2)
    finally:
        release.set()
        for thread in (holder, waiter, other):
            if thread.ident is not None:
                thread.join(timeout=5)


def test_borrow_decoder__evicts_the_least_recently_used(mocker: MockerFixture) -> None:
    mocker.patch.object(video_decoder_cache, "_DECODER_CACHE_SIZE", 2)

    for keyframe_log_time_ns in (100, 200, 300):
        with video_decoder_cache.borrow_decoder(
            uri="a.mcap", channel_id=1, keyframe_log_time_ns=keyframe_log_time_ns
        ):
            pass

    assert list(video_decoder_cache._gops) == [("a.mcap", 1, 200), ("a.mcap", 1, 300)]


def test_borrow_decoder__keeps_a_decoder_that_is_in_use(mocker: MockerFixture) -> None:
    mocker.patch.object(video_decoder_cache, "_DECODER_CACHE_SIZE", 1)

    with video_decoder_cache.borrow_decoder(uri="a.mcap", channel_id=0, keyframe_log_time_ns=100):
        with video_decoder_cache.borrow_decoder(
            uri="a.mcap", channel_id=1, keyframe_log_time_ns=100
        ):
            pass
        with video_decoder_cache.borrow_decoder(
            uri="a.mcap", channel_id=2, keyframe_log_time_ns=100
        ):
            assert ("a.mcap", 0, 100) in video_decoder_cache._gops
            assert ("a.mcap", 1, 100) not in video_decoder_cache._gops


def test_peek_decoder__no_decoder() -> None:
    assert (
        video_decoder_cache.peek_decoder(uri="a.mcap", channel_id=1, keyframe_log_time_ns=100)
        is None
    )


def test_clear() -> None:
    with video_decoder_cache.borrow_decoder(
        uri="a.mcap", channel_id=1, keyframe_log_time_ns=100
    ) as lease:
        lease.reset()
    jpeg_id = JpegId(uri="a.mcap", channel_id=1, log_time_ns=100, width=None, height=8, quality=85)
    camera_jpeg_cache.put_jpeg(jpeg_id=jpeg_id, data=b"jpeg")

    video_decoder_cache.clear()

    with video_decoder_cache.borrow_decoder(
        uri="a.mcap", channel_id=1, keyframe_log_time_ns=100
    ) as lease:
        assert lease.decoder is None
    assert camera_jpeg_cache.get_jpeg(jpeg_id=jpeg_id) is None


def _users(key: tuple[str, int, int]) -> int:
    """Waits until a second request waits for a GOP, and returns its user count."""
    deadline = time.monotonic() + 5
    while time.monotonic() < deadline:
        with video_decoder_cache._guard:
            users = video_decoder_cache._gops[key].users
        if users >= 2:
            return users
        time.sleep(0.01)
    return users
