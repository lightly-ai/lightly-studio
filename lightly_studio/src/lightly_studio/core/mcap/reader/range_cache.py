"""Shares the byte reads of a remote MCAP file across readers.

Several requests for one tick often read the same chunk. The first read downloads
it. The others wait and reuse those bytes. A reader can also download all the chunks
it needs at once before it reads them, and the chunks of the next ticks in the
background. A read is served from any downloaded range that contains it. The cache
is bounded, so it keeps the chunks around the view, not the recording.
"""

from __future__ import annotations

import io
import logging
import threading
import time
from collections.abc import Callable, Sequence
from concurrent.futures import ThreadPoolExecutor
from typing import IO, NamedTuple, cast

import fsspec.utils

from lightly_studio.core.mcap.reader import read_account
from lightly_studio.core.mcap.reader.span_store import SpanStore

logger = logging.getLogger(__name__)

# One chunk is a few hundred kilobytes to a few megabytes. A tick reads the chunks
# from the camera keyframe on, and the chunks of the next ticks are read ahead.
_MAX_BYTES = 128 * 1024 * 1024
# Chunk bodies are shared as one range. A chunk header is several reads of a few
# bytes, so those reads share one block instead of downloading once per reader.
_MIN_SHARED_BYTES = 4 * 1024
_SHARED_BLOCK_BYTES = 64 * 1024
_REMOTE_PROTOCOLS = frozenset({"s3", "gs", "gcs", "http", "https"})
# A read ahead downloads its ranges concurrently, so few workers are enough.
_READ_AHEAD_WORKERS = 2


class ByteRange(NamedTuple):
    """A range of bytes in a file.

    Attributes:
        offset: The first byte of the range.
        length: The number of bytes of the range.
    """

    offset: int
    length: int


LoadRanges = Callable[[Sequence[ByteRange]], list[bytes]]
"""Downloads several ranges of one file at once and returns their bytes in order."""


class _InFlight:
    """One byte-range download shared by the readers that need it together."""

    def __init__(self, offset: int, length: int) -> None:
        """Starts a download that has not finished."""
        self.offset = offset
        self.length = length
        self.event = threading.Event()
        self.data: bytes | None = None
        self.error: BaseException | None = None
        self.waiters = 0

    def contains(self, offset: int, length: int) -> bool:
        """Returns whether the download includes a range."""
        return self.offset <= offset and offset + length <= self.offset + self.length


class _Share(NamedTuple):
    """The bytes of a range that readers share, or the download that gets them."""

    data: bytes | None = None
    flight: _InFlight | None = None
    is_leader: bool = False


_lock = threading.Lock()
_spans = SpanStore(max_bytes=_MAX_BYTES)
_inflight: dict[tuple[str, int, int], _InFlight] = {}
_read_ahead_pool = ThreadPoolExecutor(
    max_workers=_READ_AHEAD_WORKERS, thread_name_prefix="mcap-read-ahead"
)


class SharedRangeStream(io.IOBase):
    """A stream that serves repeated reads of a remote file from `read_shared`.

    This is not a `RawIOBase`. The MCAP stream reader wraps a raw stream in its own
    buffer, which would read around this cache.
    """

    def __init__(self, raw: IO[bytes], uri: str, load_ranges: LoadRanges) -> None:
        """Wraps a stream without reading it.

        Args:
            raw: The stream that talks to storage. Closed with this wrapper.
            uri: The URI the shared reads are stored under.
            load_ranges: Downloads several ranges of the file at once. It must not
                use `raw`, because it also runs in the background.
        """
        super().__init__()
        self._raw = raw
        self._uri = uri
        self._load_ranges = load_ranges
        self._position = 0

    def readable(self) -> bool:
        """Returns whether the stream can be read."""
        return True

    def seekable(self) -> bool:
        """Returns whether the stream can be seeked."""
        return True

    def seek(self, offset: int, whence: int = io.SEEK_SET) -> int:
        """Moves the read position.

        Args:
            offset: The distance to move, in bytes.
            whence: `io.SEEK_SET`, `io.SEEK_CUR`, or `io.SEEK_END`.

        Returns:
            The new position.
        """
        if whence == io.SEEK_SET:
            self._position = offset
        elif whence == io.SEEK_CUR:
            self._position += offset
        elif whence == io.SEEK_END:
            self._raw.seek(0, io.SEEK_END)
            self._position = self._raw.tell() + offset
        else:
            raise ValueError(f"Unsupported seek whence: {whence}.")
        return self._position

    def tell(self) -> int:
        """Returns the read position."""
        return self._position

    def read(self, size: int = -1) -> bytes:
        """Reads `size` bytes, sharing a range that is downloaded or downloading.

        Args:
            size: The number of bytes to read. A negative size reads through the
                end of the stream and is not shared. A read that no shared range
                contains is downloaded, a read smaller than a chunk body as one
                shared block.

        Returns:
            The bytes at the current position.
        """
        if size < 0:
            return self._read_through_end()
        if size == 0:
            return b""
        offset = self._position
        data = _take_share(
            share=_join(uri=self._uri, offset=offset, length=size, lead=False),
            offset=offset,
            length=size,
        )
        if data is None:
            data = self._download(offset=offset, size=size)
        return self._remember(offset=offset, data=data)

    def fetch(self, ranges: Sequence[ByteRange]) -> None:
        """Downloads the ranges that no reader has or is downloading, all at once."""
        fetch_ranges(uri=self._uri, ranges=ranges, load_ranges=self._load_ranges)

    def fetch_in_background(self, ranges: Sequence[ByteRange]) -> None:
        """Starts `fetch` on a background thread and returns at once."""
        _read_ahead_pool.submit(
            fetch_ranges, uri=self._uri, ranges=list(ranges), load_ranges=self._load_ranges
        )

    def close(self) -> None:
        """Closes the wrapped stream."""
        if self.closed:
            return
        self._raw.close()
        super().close()

    def _download(self, offset: int, size: int) -> bytes:
        """Downloads a read that no shared range contains, and shares it."""
        if size < _MIN_SHARED_BYTES:
            return _read_from_shared_block(
                uri=self._uri, offset=offset, size=size, read_raw=self._read_raw
            )
        return read_shared(
            uri=self._uri,
            offset=offset,
            length=size,
            load=lambda: self._read_raw(offset=offset, size=size),
        )

    def _read_through_end(self) -> bytes:
        """Reads from the current position to the end, without sharing the read."""
        offset = self._position
        return self._remember(offset=offset, data=self._read_raw(offset=offset, size=-1))

    def _remember(self, offset: int, data: bytes) -> bytes:
        """Advances the position past `data` and returns it."""
        self._position = offset + len(data)
        return data

    def _read_raw(self, offset: int, size: int) -> bytes:
        """Reads `size` bytes from the wrapped stream at `offset`."""
        self._raw.seek(offset)
        return self._raw.read(size)


def share_remote_reads(stream: IO[bytes], uri: str, load_ranges: LoadRanges) -> IO[bytes]:
    """Returns a stream whose reads of a remote file are shared across readers.

    Args:
        stream: The stream that talks to storage.
        uri: The path or URI of the file. A local path is returned unchanged.
        load_ranges: Downloads several ranges of the file at once, for `fetch`.

    Returns:
        `stream` for a local path, otherwise a stream that shares identical reads.
    """
    if fsspec.utils.get_protocol(uri) not in _REMOTE_PROTOCOLS:
        return stream
    return cast(IO[bytes], SharedRangeStream(raw=stream, uri=uri, load_ranges=load_ranges))


def fetch(stream: IO[bytes], ranges: Sequence[ByteRange]) -> None:
    """Downloads the ranges a stream will read, all at once, and waits for them.

    Args:
        stream: A stream from `share_remote_reads`. A stream that does not share
            reads, e.g. of a local file, downloads nothing.
        ranges: The ranges to download. A range that is cached or downloading is
            skipped.
    """
    if isinstance(stream, SharedRangeStream):
        stream.fetch(ranges)


def fetch_in_background(stream: IO[bytes], ranges: Sequence[ByteRange]) -> None:
    """Starts to download the ranges a stream will read later, and returns at once.

    Args:
        stream: A stream from `share_remote_reads`. A stream that does not share
            reads, e.g. of a local file, downloads nothing.
        ranges: The ranges to download. A range that is cached or downloading is
            skipped.
    """
    if isinstance(stream, SharedRangeStream):
        stream.fetch_in_background(ranges)


def fetch_ranges(uri: str, ranges: Sequence[ByteRange], load_ranges: LoadRanges) -> None:
    """Downloads the ranges that no reader has or is downloading, all at once.

    A reader of one of the ranges waits for this download. If the download fails,
    the failure is logged and the reader downloads the range itself.

    Args:
        uri: The URI the ranges are stored under.
        ranges: The ranges to download.
        load_ranges: Downloads several ranges of the file at once.
    """
    flights = _claim(uri=uri, ranges=ranges)
    if not flights:
        return
    try:
        _load_flights(uri=uri, flights=flights, load_ranges=load_ranges)
    finally:
        for flight in flights:
            _finish(uri=uri, flight=flight)


def read_shared(uri: str, offset: int, length: int, load: Callable[[], bytes]) -> bytes:
    """Returns the bytes at a range, downloading them once when callers race.

    Args:
        uri: The URI the range belongs to.
        offset: The first byte of the range.
        length: The number of bytes requested.
        load: Reads the range from storage. Called once for a range.

    Returns:
        The bytes at the range.
    """
    if length > _MAX_BYTES:
        return _load_accounted(load)
    share = _join(uri=uri, offset=offset, length=length, lead=True)
    data = _take_share(share=share, offset=offset, length=length)
    if data is not None:
        return data
    if not share.is_leader:
        # The download this read waited for did not finish, e.g. a failed read ahead.
        return _load_accounted(load)
    assert share.flight is not None
    return _lead(uri=uri, flight=share.flight, load=load)


def clear() -> None:
    """Drops cached ranges and releases readers waiting on a download."""
    with _lock:
        flights = list(_inflight.values())
        _spans.clear()
        _inflight.clear()
    for flight in flights:
        flight.event.set()


def _read_from_shared_block(
    uri: str,
    offset: int,
    size: int,
    read_raw: Callable[[int, int], bytes],
) -> bytes:
    """Returns a short read from the shared block that contains it.

    The reads of one chunk header fall in the same block, so the first reader
    downloads the block and the others take their bytes from it.

    Args:
        uri: The URI the block belongs to.
        offset: The first byte to return.
        size: The number of bytes to return.
        read_raw: Reads a block from storage. Called once for a block.

    Returns:
        The bytes at `offset`. Empty when `offset` is past the end of the block.
    """
    pieces: list[bytes] = []
    cursor = offset
    end = offset + size
    while cursor < end:
        block_start = cursor - (cursor % _SHARED_BLOCK_BYTES)
        block = _shared_block(uri=uri, block_start=block_start, read_raw=read_raw)
        local_start = cursor - block_start
        if local_start >= len(block):
            break
        local_end = min(end - block_start, len(block))
        pieces.append(block[local_start:local_end])
        cursor = block_start + local_end
    return b"".join(pieces)


def _shared_block(uri: str, block_start: int, read_raw: Callable[[int, int], bytes]) -> bytes:
    """Returns one shared block, downloading it when no reader has it yet."""
    return read_shared(
        uri=uri,
        offset=block_start,
        length=_SHARED_BLOCK_BYTES,
        load=lambda: read_raw(block_start, _SHARED_BLOCK_BYTES),
    )


def _join(uri: str, offset: int, length: int, lead: bool) -> _Share:
    """Finds the cached bytes or the download of a range, or starts the download.

    Args:
        uri: The URI the range belongs to.
        offset: The first byte of the range.
        length: The number of bytes of the range.
        lead: Whether to start a download when no reader has the range.

    Returns:
        The cached bytes, the download that contains the range, or neither when
        nothing contains the range and `lead` is false.
    """
    with _lock:
        data = _spans.get(uri=uri, offset=offset, length=length)
        if data is not None:
            return _Share(data=data)
        flight = _containing_flight(uri=uri, offset=offset, length=length)
        if flight is not None:
            flight.waiters += 1
            return _Share(flight=flight)
        if not lead:
            return _Share()
        flight = _InFlight(offset=offset, length=length)
        _inflight[(uri, offset, length)] = flight
        return _Share(flight=flight, is_leader=True)


def _take_share(share: _Share, offset: int, length: int) -> bytes | None:
    """Returns the bytes of a share, waiting for its download.

    Returns:
        The bytes at the range. `None` when the share leads its download, has no
        download, or its download finished without bytes.
    """
    if share.data is not None:
        read_account.note_hit(byte_count=len(share.data))
        return share.data
    if share.flight is None or share.is_leader:
        return None
    return _wait_accounted(flight=share.flight, offset=offset, length=length)


def _claim(uri: str, ranges: Sequence[ByteRange]) -> list[_InFlight]:
    """Starts the downloads of the ranges that no reader has or is downloading."""
    flights: list[_InFlight] = []
    with _lock:
        for byte_range in ranges:
            if byte_range.length > _MAX_BYTES or _is_shared(uri=uri, byte_range=byte_range):
                continue
            flight = _InFlight(offset=byte_range.offset, length=byte_range.length)
            _inflight[(uri, byte_range.offset, byte_range.length)] = flight
            flights.append(flight)
    return flights


def _is_shared(uri: str, byte_range: ByteRange) -> bool:
    """Returns whether a range is cached or downloading. The caller holds `_lock`."""
    return _spans.contains(uri=uri, offset=byte_range.offset, length=byte_range.length) or bool(
        _containing_flight(uri=uri, offset=byte_range.offset, length=byte_range.length)
    )


def _containing_flight(uri: str, offset: int, length: int) -> _InFlight | None:
    """Returns a download that contains a range. The caller holds `_lock`."""
    for (flight_uri, _, _), flight in _inflight.items():
        if flight_uri == uri and flight.contains(offset=offset, length=length):
            return flight
    return None


def _load_flights(uri: str, flights: Sequence[_InFlight], load_ranges: LoadRanges) -> None:
    """Downloads the ranges of several downloads at once and stores their bytes."""
    started = time.perf_counter()
    try:
        datas = load_ranges([ByteRange(offset=f.offset, length=f.length) for f in flights])
    except Exception:
        logger.warning("Cannot download %s ranges of '%s'.", len(flights), uri, exc_info=True)
        return
    read_account.note_load(
        byte_count=sum(len(data) for data in datas), seconds=time.perf_counter() - started
    )
    with _lock:
        for flight, data in zip(flights, datas):
            flight.data = data
            _spans.put(uri=uri, offset=flight.offset, data=data)


def _lead(uri: str, flight: _InFlight, load: Callable[[], bytes]) -> bytes:
    """Downloads the range of a download this reader leads, and shares it."""
    started = time.perf_counter()
    try:
        data = load()
    except Exception as error:
        flight.error = error
        raise
    else:
        read_account.note_load(byte_count=len(data), seconds=time.perf_counter() - started)
        with _lock:
            flight.data = data
            _spans.put(uri=uri, offset=flight.offset, data=data)
        return data
    finally:
        _finish(uri=uri, flight=flight)


def _load_accounted(load: Callable[[], bytes]) -> bytes:
    """Reads from storage and counts the time."""
    started = time.perf_counter()
    data = load()
    read_account.note_load(byte_count=len(data), seconds=time.perf_counter() - started)
    return data


def _wait_accounted(flight: _InFlight, offset: int, length: int) -> bytes | None:
    """Waits for a download another reader is doing and counts the wait.

    Returns:
        The bytes at the range, or `None` if the download finished without bytes.

    Raises:
        Exception: The downloading reader failed. The same error is raised here.
    """
    started = time.perf_counter()
    flight.event.wait()
    if flight.error is not None:
        raise flight.error
    if flight.data is None:
        return None
    local_start = offset - flight.offset
    data = flight.data[local_start : local_start + length]
    read_account.note_wait(byte_count=len(data), seconds=time.perf_counter() - started)
    return data


def _finish(uri: str, flight: _InFlight) -> None:
    """Wakes the readers waiting on a download."""
    with _lock:
        _inflight.pop((uri, flight.offset, flight.length), None)
    flight.event.set()
