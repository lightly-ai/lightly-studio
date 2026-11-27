"""Shares in-flight byte reads of a remote MCAP file across readers.

Several requests for one tick often read the same chunk. The first read downloads
it. The others wait and reuse those bytes. The cache is bounded, so it keeps the
chunks currently being read, not the recording.
"""

from __future__ import annotations

import io
import threading
from collections import OrderedDict
from collections.abc import Callable
from typing import IO, cast

import fsspec.utils

# One chunk is a few hundred kilobytes. Sixteen megabytes covers the chunks a
# page reads at once, and drops them as the view moves on.
_MAX_BYTES = 16 * 1024 * 1024
# Chunk bodies are shared as one range. A chunk header is several reads of a few
# bytes, so those reads share one block instead of downloading once per reader.
_MIN_SHARED_BYTES = 4 * 1024
_SHARED_BLOCK_BYTES = 64 * 1024
_REMOTE_PROTOCOLS = frozenset({"s3", "gs", "gcs", "http", "https"})


class SharedRangeStream(io.IOBase):
    """A stream that serves repeated reads of a remote file from `read_shared`.

    This is not a `RawIOBase`. The MCAP stream reader wraps a raw stream in its own
    buffer, which would read around this cache.
    """

    def __init__(self, raw: IO[bytes], uri: str) -> None:
        """Wraps a stream without reading it.

        Args:
            raw: The stream that talks to storage. Closed with this wrapper.
            uri: The URI the shared reads are stored under.
        """
        super().__init__()
        self._raw = raw
        self._uri = uri
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
        """Reads `size` bytes, sharing an identical read that is already running.

        Args:
            size: The number of bytes to read. A negative size reads through the
                end of the stream and is not shared. A read shorter than
                `_MIN_SHARED_BYTES` comes from shared blocks.

        Returns:
            The bytes at the current position.
        """
        offset = self._position
        if size < 0:
            data = self._read_raw(offset=offset, size=-1)
        elif size == 0:
            data = b""
        elif size < _MIN_SHARED_BYTES:
            data = _read_from_shared_block(
                uri=self._uri, offset=offset, size=size, read_raw=self._read_raw
            )
        else:
            data = read_shared(
                uri=self._uri,
                offset=offset,
                length=size,
                load=lambda: self._read_raw(offset=offset, size=size),
            )
        self._position = offset + len(data)
        return data

    def close(self) -> None:
        """Closes the wrapped stream."""
        if self.closed:
            return
        self._raw.close()
        super().close()

    def _read_raw(self, offset: int, size: int) -> bytes:
        """Reads `size` bytes from the wrapped stream at `offset`."""
        self._raw.seek(offset)
        return self._raw.read(size)


class _Usage:
    """How many cached bytes are stored. A class, so that it changes without `global`."""

    def __init__(self) -> None:
        """Starts with nothing stored."""
        self.cached_bytes = 0


class _InFlight:
    """One byte-range download shared by the readers that need it together."""

    def __init__(self) -> None:
        """Starts a download that has not finished."""
        self.event = threading.Event()
        self.data: bytes | None = None
        self.error: BaseException | None = None
        self.waiters = 0


_lock = threading.Lock()
_ranges: OrderedDict[tuple[str, int, int], bytes] = OrderedDict()
_usage = _Usage()
_inflight: dict[tuple[str, int, int], _InFlight] = {}


def share_remote_reads(stream: IO[bytes], uri: str) -> IO[bytes]:
    """Returns a stream whose reads of a remote file are shared across readers.

    Args:
        stream: The stream that talks to storage.
        uri: The path or URI of the file. A local path is returned unchanged.

    Returns:
        `stream` for a local path, otherwise a stream that shares identical reads.
    """
    if not is_remote_uri(uri=uri):
        return stream
    return cast(IO[bytes], SharedRangeStream(raw=stream, uri=uri))


def is_remote_uri(uri: str) -> bool:
    """Returns whether a path or URI names a file in cloud storage or on a web server."""
    return fsspec.utils.get_protocol(uri) in _REMOTE_PROTOCOLS


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
        return load()
    key = (uri, offset, length)
    cached = _take(key)
    if cached is not None:
        return cached
    flight, is_leader = _join(key)
    if flight is None:
        cached = _take(key)
        return load() if cached is None else cached
    if not is_leader:
        return _wait(flight=flight, load=load)
    try:
        data = load()
    except Exception as error:
        flight.error = error
        raise
    else:
        flight.data = data
        _store(key=key, data=data)
        return data
    finally:
        _finish(key=key, flight=flight)


def clear() -> None:
    """Drops cached ranges and releases readers waiting on a download."""
    with _lock:
        flights = list(_inflight.values())
        _ranges.clear()
        _usage.cached_bytes = 0
        _inflight.clear()
    for flight in flights:
        flight.event.set()


def _read_from_shared_block(
    uri: str,
    offset: int,
    size: int,
    read_raw: Callable[[int, int], bytes],
) -> bytes:
    """Returns a short read from the shared blocks that contain it.

    The reads of one chunk header fall in the same block. The first reader
    downloads the block, and the others take their bytes from it.

    Args:
        uri: The URI the block belongs to.
        offset: The first byte to return.
        size: The number of bytes to return.
        read_raw: Reads a block from storage. Called once for a block.

    Returns:
        The bytes at `offset`. Fewer bytes at the end of the file.
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


def _wait(flight: _InFlight, load: Callable[[], bytes]) -> bytes:
    """Waits for a download another reader is doing.

    Reads the range with `load` when the cache was cleared during the wait.

    Raises:
        Exception: The downloading reader failed. The same error is raised here.
    """
    flight.event.wait()
    if flight.error is not None:
        raise flight.error
    if flight.data is None:
        return load()
    return flight.data


def _take(key: tuple[str, int, int]) -> bytes | None:
    """Returns a cached range, marking it as recently used."""
    with _lock:
        data = _ranges.get(key)
        if data is None:
            return None
        _ranges.move_to_end(key)
        return data


def _join(key: tuple[str, int, int]) -> tuple[_InFlight | None, bool]:
    """Joins the download of a range, or reports that the cache now holds it.

    Returns:
        The in-flight download and whether this caller reads storage. The
        download is `None` when another caller stored the range first.
    """
    with _lock:
        if key in _ranges:
            _ranges.move_to_end(key)
            return None, False
        flight = _inflight.get(key)
        if flight is None:
            flight = _InFlight()
            _inflight[key] = flight
            return flight, True
        flight.waiters += 1
        return flight, False


def _finish(key: tuple[str, int, int], flight: _InFlight) -> None:
    """Wakes the readers waiting on a download."""
    with _lock:
        _inflight.pop(key, None)
    flight.event.set()


def _store(key: tuple[str, int, int], data: bytes) -> None:
    """Stores a range and drops the least recently used ones past the bound."""
    if len(data) > _MAX_BYTES:
        return
    with _lock:
        previous = _ranges.pop(key, None)
        if previous is not None:
            _usage.cached_bytes -= len(previous)
        _ranges[key] = data
        _usage.cached_bytes += len(data)
        while _ranges and _usage.cached_bytes > _MAX_BYTES:
            _, dropped = _ranges.popitem(last=False)
            _usage.cached_bytes -= len(dropped)
