"""Tests for sharing in-flight reads of a remote MCAP file."""

from __future__ import annotations

import io
import threading
import time
from collections.abc import Callable, Iterator, Sequence

import pytest

from lightly_studio.core.mcap.reader import range_cache
from lightly_studio.core.mcap.reader.range_cache import ByteRange, SharedRangeStream
from lightly_studio.core.mcap.reader.span_store import SpanStore

_URI = "s3://bucket/recording.mcap"


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


def test_read_shared__drops_the_oldest_range(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(range_cache, "_spans", SpanStore(max_bytes=4))
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
    first = SharedRangeStream(raw=_Raw(payload), uri=_URI, load_ranges=_unused_load_ranges)
    second = SharedRangeStream(raw=_Raw(payload), uri=_URI, load_ranges=_unused_load_ranges)
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

    first = SharedRangeStream(raw=_Raw(b"hello-mcap"), uri=_URI, load_ranges=_unused_load_ranges)
    second = SharedRangeStream(raw=_Raw(b"hello-mcap"), uri=_URI, load_ranges=_unused_load_ranges)
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
            stream = SharedRangeStream(raw=_Raw(payload), uri=_URI, load_ranges=_unused_load_ranges)
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

    stream = SharedRangeStream(raw=_Raw(b"hello-mcap"), uri=_URI, load_ranges=_unused_load_ranges)
    assert stream.read(2) == b"he"
    stream.seek(4)
    assert stream.read(2) == b"o-"

    assert raw_reads == 2


def test_shared_range_stream__reads_inside_a_fetched_range_do_not_read_storage(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(range_cache, "_MIN_SHARED_BYTES", 4)
    payload = b"0123456789"
    stream = SharedRangeStream(
        raw=_RawWithoutReads(),
        uri=_URI,
        load_ranges=lambda ranges: [payload[r.offset : r.offset + r.length] for r in ranges],
    )

    stream.fetch([ByteRange(offset=0, length=10)])
    stream.seek(2)

    assert stream.read(2) == b"23"
    assert stream.read(5) == b"45678"


def test_shared_range_stream__fetch_in_background() -> None:
    loading = threading.Event()

    def load_ranges(_ranges: Sequence[ByteRange]) -> list[bytes]:
        loading.set()
        return [b"0123456789"]

    stream = SharedRangeStream(raw=_RawWithoutReads(), uri=_URI, load_ranges=load_ranges)

    stream.fetch_in_background([ByteRange(offset=0, length=10)])
    assert loading.wait(timeout=5)
    stream.seek(3)

    assert stream.read(2) == b"34"


def test_fetch_ranges__downloads_the_ranges_together() -> None:
    calls: list[list[ByteRange]] = []

    def load_ranges(ranges: Sequence[ByteRange]) -> list[bytes]:
        calls.append(list(ranges))
        return [b"aaaa", b"bbbb"]

    range_cache.fetch_ranges(
        uri=_URI,
        ranges=[ByteRange(offset=0, length=4), ByteRange(offset=4, length=4)],
        load_ranges=load_ranges,
    )

    assert calls == [[ByteRange(offset=0, length=4), ByteRange(offset=4, length=4)]]
    assert range_cache.read_shared(uri=_URI, offset=4, length=4, load=_unused_load) == b"bbbb"


def test_fetch_ranges__skips_cached_ranges() -> None:
    range_cache.read_shared(uri=_URI, offset=0, length=8, load=lambda: b"aaaabbbb")
    calls: list[list[ByteRange]] = []

    def load_ranges(ranges: Sequence[ByteRange]) -> list[bytes]:
        calls.append(list(ranges))
        return [b"cccc"]

    range_cache.fetch_ranges(
        uri=_URI,
        ranges=[ByteRange(offset=4, length=4), ByteRange(offset=8, length=4)],
        load_ranges=load_ranges,
    )

    assert calls == [[ByteRange(offset=8, length=4)]]


def test_fetch_ranges__reader_waits_for_the_download() -> None:
    entered = threading.Event()
    release = threading.Event()

    def load_ranges(_ranges: Sequence[ByteRange]) -> list[bytes]:
        entered.set()
        if not release.wait(timeout=5):
            raise TimeoutError("The download was not released.")
        return [b"0123456789"]

    results = _read_while_fetching(
        load_ranges=load_ranges, load=_unused_load, entered=entered, release=release
    )

    assert results == [b"234"]


def test_fetch_ranges__failed_download_lets_the_reader_load() -> None:
    entered = threading.Event()
    release = threading.Event()

    def load_ranges(_ranges: Sequence[ByteRange]) -> list[bytes]:
        entered.set()
        release.wait(timeout=5)
        raise OSError("The download failed.")

    results = _read_while_fetching(
        load_ranges=load_ranges, load=lambda: b"234", entered=entered, release=release
    )

    assert results == [b"234"]


def _read_while_fetching(
    load_ranges: range_cache.LoadRanges,
    load: Callable[[], bytes],
    entered: threading.Event,
    release: threading.Event,
) -> list[bytes]:
    """Reads bytes 2 to 4 while `load_ranges` downloads bytes 0 to 9."""
    results: list[bytes] = []
    fetcher = threading.Thread(
        target=range_cache.fetch_ranges,
        kwargs={
            "uri": _URI,
            "ranges": [ByteRange(offset=0, length=10)],
            "load_ranges": load_ranges,
        },
    )
    reader = threading.Thread(
        target=lambda: results.append(
            range_cache.read_shared(uri=_URI, offset=2, length=3, load=load)
        )
    )
    fetcher.start()
    try:
        assert entered.wait(timeout=5)
        reader.start()
        assert _follower_is_waiting(), "The reader did not wait for the download."
    finally:
        release.set()
        fetcher.join(timeout=5)
        if reader.ident is not None:
            reader.join(timeout=5)
    return results


class _RawWithoutReads(io.BytesIO):
    """A storage stream that fails a test that reads it."""

    def read(self, _size: int | None = -1) -> bytes:
        raise AssertionError("The stream read storage.")


def _unused_load() -> bytes:
    raise AssertionError("The range was read from storage.")


def _unused_load_ranges(_ranges: Sequence[ByteRange]) -> list[bytes]:
    raise AssertionError("The ranges were read from storage.")


def _follower_is_waiting() -> bool:
    """Returns whether a second caller is waiting on the in-flight range."""
    deadline = time.monotonic() + 5
    while time.monotonic() < deadline:
        with range_cache._lock:
            if any(flight.waiters >= 1 for flight in range_cache._inflight.values()):
                return True
        time.sleep(0.01)
    return False
