"""Tests for sharing in-flight reads of a remote MCAP file."""

from __future__ import annotations

import io
import threading
import time
from collections.abc import Callable, Iterator

import pytest

from lightly_studio.core.mcap.reader import range_cache
from lightly_studio.core.mcap.reader.range_cache import SharedRangeStream


@pytest.fixture(autouse=True)
def clear_range_cache() -> Iterator[None]:
    range_cache.clear()
    yield
    range_cache.clear()


def test_read_shared__reuses_bytes() -> None:
    loads = 0

    def load() -> bytes:
        nonlocal loads
        loads += 1
        return b"chunk"

    first = range_cache.read_shared(uri="s3://bucket/recording.mcap", offset=0, length=5, load=load)
    second = range_cache.read_shared(
        uri="s3://bucket/recording.mcap", offset=0, length=5, load=load
    )

    assert first == second == b"chunk"
    assert loads == 1


def test_read_shared__single_flight() -> None:
    entered = threading.Event()
    release = threading.Event()
    loads = 0
    errors: list[BaseException] = []

    def load() -> bytes:
        nonlocal loads
        loads += 1
        entered.set()
        if not release.wait(timeout=5):
            raise TimeoutError("The range read was not released.")
        return b"chunk"

    def read() -> None:
        try:
            range_cache.read_shared(uri="s3://bucket/recording.mcap", offset=8, length=5, load=load)
        except Exception as error:
            errors.append(error)

    leader = threading.Thread(target=read)
    follower = threading.Thread(target=read)
    leader.start()
    try:
        assert entered.wait(timeout=5)
        follower.start()
        assert _follower_is_waiting(), "The second reader did not wait for the range."
        release.set()
        leader.join(timeout=5)
        follower.join(timeout=5)
    finally:
        release.set()
        leader.join(timeout=5)
        if follower.ident is not None:
            follower.join(timeout=5)

    assert errors == []
    assert not leader.is_alive()
    assert not follower.is_alive()
    assert loads == 1


def test_read_shared__waiter_reads_storage_after_clear() -> None:
    entered = threading.Event()
    release = threading.Event()
    results: list[bytes] = []
    errors: list[BaseException] = []

    def load_blocked() -> bytes:
        entered.set()
        if not release.wait(timeout=5):
            raise TimeoutError("The range read was not released.")
        return b"chunk"

    def read(load: Callable[[], bytes]) -> None:
        try:
            results.append(
                range_cache.read_shared(
                    uri="s3://bucket/recording.mcap", offset=8, length=5, load=load
                )
            )
        except Exception as error:
            errors.append(error)

    leader = threading.Thread(target=read, kwargs={"load": load_blocked})
    follower = threading.Thread(target=read, kwargs={"load": lambda: b"fresh"})
    leader.start()
    try:
        assert entered.wait(timeout=5)
        follower.start()
        assert _follower_is_waiting(), "The second reader did not wait for the range."
        range_cache.clear()
        follower.join(timeout=5)
        assert not follower.is_alive()
        assert results == [b"fresh"]
    finally:
        release.set()
        leader.join(timeout=5)
        if follower.ident is not None:
            follower.join(timeout=5)

    assert errors == []
    assert results == [b"fresh", b"chunk"]


def test_read_shared__drops_the_oldest_range(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(range_cache, "_MAX_BYTES", 4)
    range_cache.read_shared(
        uri="s3://bucket/recording.mcap", offset=0, length=4, load=lambda: b"aaaa"
    )
    range_cache.read_shared(
        uri="s3://bucket/recording.mcap", offset=4, length=4, load=lambda: b"bbbb"
    )

    loads = 0

    def load_oldest() -> bytes:
        nonlocal loads
        loads += 1
        return b"aaaa"

    range_cache.read_shared(uri="s3://bucket/recording.mcap", offset=0, length=4, load=load_oldest)

    assert loads == 1


def test_shared_range_stream__second_stream_does_not_read_storage(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(range_cache, "_MIN_SHARED_BYTES", 4)
    raw_reads = 0

    class _Raw(io.BytesIO):
        def read(self, size: int | None = -1) -> bytes:
            nonlocal raw_reads
            raw_reads += 1
            return super().read(size)

    payload = b"hello-mcap"
    first = SharedRangeStream(raw=_Raw(payload), uri="s3://bucket/recording.mcap")
    second = SharedRangeStream(raw=_Raw(payload), uri="s3://bucket/recording.mcap")
    assert first.read(len(payload)) == payload
    assert second.read(len(payload)) == payload

    assert raw_reads == 1


def test_shared_range_stream__small_read_is_shared() -> None:
    raw_reads = 0

    class _Raw(io.BytesIO):
        def read(self, size: int | None = -1) -> bytes:
            nonlocal raw_reads
            raw_reads += 1
            return super().read(size)

    first = SharedRangeStream(raw=_Raw(b"hello-mcap"), uri="s3://bucket/recording.mcap")
    second = SharedRangeStream(raw=_Raw(b"hello-mcap"), uri="s3://bucket/recording.mcap")
    assert first.read(5) == b"hello"
    second.seek(5)
    assert second.read(4) == b"-mca"

    assert raw_reads == 1


def test_shared_range_stream__small_reads_at_different_offsets_download_once() -> None:
    entered = threading.Event()
    release = threading.Event()
    raw_reads = 0
    errors: list[BaseException] = []
    payload = b"hello-mcap-bytes"

    class _Raw(io.BytesIO):
        def read(self, size: int | None = -1) -> bytes:
            nonlocal raw_reads
            raw_reads += 1
            entered.set()
            if not release.wait(timeout=5):
                raise TimeoutError("The block read was not released.")
            return super().read(size)

    def read_at(offset: int, size: int) -> None:
        try:
            stream = SharedRangeStream(raw=_Raw(payload), uri="s3://bucket/recording.mcap")
            stream.seek(offset)
            if stream.read(size) != payload[offset : offset + size]:
                raise AssertionError("The shared block returned the wrong bytes.")
        except Exception as error:
            errors.append(error)

    leader = threading.Thread(target=read_at, kwargs={"offset": 0, "size": 5})
    follower = threading.Thread(target=read_at, kwargs={"offset": 5, "size": 4})
    leader.start()
    try:
        assert entered.wait(timeout=5)
        follower.start()
        assert _follower_is_waiting(), "The second reader did not wait for the block."
        release.set()
        leader.join(timeout=5)
        follower.join(timeout=5)
    finally:
        release.set()
        leader.join(timeout=5)
        if follower.ident is not None:
            follower.join(timeout=5)

    assert errors == []
    assert raw_reads == 1


def test_shared_range_stream__small_read_past_the_block_reads_again(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(range_cache, "_SHARED_BLOCK_BYTES", 4)
    raw_reads = 0

    class _Raw(io.BytesIO):
        def read(self, size: int | None = -1) -> bytes:
            nonlocal raw_reads
            raw_reads += 1
            return super().read(size)

    stream = SharedRangeStream(raw=_Raw(b"hello-mcap"), uri="s3://bucket/recording.mcap")
    assert stream.read(2) == b"he"
    stream.seek(4)
    assert stream.read(2) == b"o-"

    assert raw_reads == 2


def _follower_is_waiting() -> bool:
    """Returns whether a second caller is waiting on the in-flight range."""
    deadline = time.monotonic() + 5
    while time.monotonic() < deadline:
        with range_cache._lock:
            if any(flight.waiters >= 1 for flight in range_cache._inflight.values()):
                return True
        time.sleep(0.01)
    return False
