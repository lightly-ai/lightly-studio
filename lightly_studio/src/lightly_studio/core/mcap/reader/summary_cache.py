"""Process-wide cache of parsed MCAP summaries for remote files.

Opening a remote MCAP file reads its summary section (channels, schemas, and the
chunk index) before it can range-read a message chunk. That section is the same
for every reader of a file. The cache keeps one parsed summary per URI, so later
readers skip the download. Chunk bytes are not cached: each reader still fetches
the chunks it needs, on its own stream.
"""

from __future__ import annotations

import threading
from collections import OrderedDict
from typing import cast

import fsspec.utils
from mcap.reader import McapReader, SeekingReader
from mcap.summary import Summary

# One summary is a few megabytes. Thirty-two recordings stay well under the size
# of the chunk bytes a block cache would keep per reader.
_CACHE_SIZE = 32
_REMOTE_PROTOCOLS = frozenset({"s3", "gs", "gcs", "http", "https"})


class _InFlight:
    """A summary download shared by the readers that open one URI together."""

    def __init__(self) -> None:
        """Starts a download that has not finished."""
        self.event = threading.Event()
        self.summary: Summary | None = None
        self.error: BaseException | None = None
        self.waiters = 0


_lock = threading.Lock()
_summaries: OrderedDict[str, Summary] = OrderedDict()
_inflight: dict[str, _InFlight] = {}


def install_cached_summary(reader: McapReader, uri: str) -> None:
    """Gives a remote reader the cached summary of its file.

    The first reader of a URI reads the summary and stores it. Later readers,
    including ones opened while that read is still in progress, reuse the parsed
    summary, so the summary section is downloaded once.

    Args:
        reader: The seeking reader just opened for `uri`.
        uri: The path or URI of the MCAP file. Local paths are left unchanged.
    """
    if not _caches_summary(uri):
        return
    summary = _take_cached(uri)
    if summary is None:
        summary = _load_once(reader=reader, uri=uri)
    if summary is not None:
        _use_cached_summary(reader=reader, summary=summary)


def clear() -> None:
    """Drops every cached summary and releases readers waiting on a download."""
    with _lock:
        flights = list(_inflight.values())
        _summaries.clear()
        _inflight.clear()
    for flight in flights:
        flight.event.set()


def _load_once(reader: McapReader, uri: str) -> Summary | None:
    """Reads the summary of a URI once when several readers open it together.

    Returns:
        The parsed summary, or `None` when the file has no summary section.
    """
    flight, is_leader = _join_load(uri)
    if flight is None:
        return _take_cached(uri)
    if not is_leader:
        return _wait_for_summary(flight=flight)
    try:
        return _read_and_store(reader=reader, uri=uri, flight=flight)
    finally:
        _finish_load(uri=uri, flight=flight)


def _join_load(uri: str) -> tuple[_InFlight | None, bool]:
    """Joins the download of a URI, or reports that the cache already holds it.

    Returns:
        The in-flight download and whether this caller reads the file. The
        download is `None` when another caller stored the summary first.
    """
    with _lock:
        if uri in _summaries:
            _summaries.move_to_end(uri)
            return None, False
        flight = _inflight.get(uri)
        if flight is None:
            flight = _InFlight()
            _inflight[uri] = flight
            return flight, True
        return flight, False


def _read_and_store(reader: McapReader, uri: str, flight: _InFlight) -> Summary | None:
    """Reads the summary and stores it for the readers waiting on this download.

    Returns:
        The parsed summary, or `None` when the file has no summary section.

    Raises:
        Exception: The reader failed while reading the summary. Waiters raise
            the same error.
    """
    try:
        summary = reader.get_summary()
    except Exception as error:
        flight.error = error
        raise
    if summary is not None:
        _store(uri=uri, summary=summary)
    flight.summary = summary
    return summary


def _finish_load(uri: str, flight: _InFlight) -> None:
    """Wakes the readers waiting on a download."""
    with _lock:
        _inflight.pop(uri, None)
    flight.event.set()


def _wait_for_summary(flight: _InFlight) -> Summary | None:
    """Waits for the reader that is downloading a summary.

    Returns:
        The parsed summary, or `None` when the file has no summary section.

    Raises:
        Exception: The downloading reader failed. The same error is raised here.
    """
    with _lock:
        flight.waiters += 1
    flight.event.wait()
    if flight.error is not None:
        raise flight.error
    return flight.summary


def _take_cached(uri: str) -> Summary | None:
    """Returns the cached summary of a URI, marking it as recently used."""
    with _lock:
        summary = _summaries.get(uri)
        if summary is None:
            return None
        _summaries.move_to_end(uri)
        return summary


def _store(uri: str, summary: Summary) -> None:
    """Stores a summary and drops the least recently used ones past the bound."""
    with _lock:
        _summaries[uri] = summary
        _summaries.move_to_end(uri)
        while len(_summaries) > _CACHE_SIZE:
            _summaries.popitem(last=False)


def _use_cached_summary(reader: McapReader, summary: Summary) -> None:
    """Points a reader at a summary it does not have to download.

    `SeekingReader` has no public way to receive a summary. `get_summary`
    returns this attribute without reading the stream once it is set.
    """
    seeking_reader = cast("SeekingReader", reader)
    seeking_reader._summary = summary  # noqa: SLF001


def _caches_summary(uri: str) -> bool:
    """Returns whether a URI's summary is shared across readers.

    Local paths are read again each time. A test can rewrite a file, and a
    local summary is cheap. Remote files are treated as immutable at a URI.
    """
    return fsspec.utils.get_protocol(uri) in _REMOTE_PROTOCOLS
