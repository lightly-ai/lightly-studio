"""Process-wide cache of dynamic transforms read from a remote MCAP file.

Several point clouds on one tick ask for `/tf` a few milliseconds apart. Each
lookup reads the chunks that hold those messages. The cache keeps the edges of
one time bucket, so the first lookup reads them and the others reuse the edges.
"""

from __future__ import annotations

import threading
from collections import OrderedDict
from collections.abc import Callable

import fsspec.utils

from lightly_studio.core.mcap.type_definitions import StaticTransform

# One bucket matches the lookup window. A few hundred buckets are a few thousand
# poses, far smaller than the chunks they were read from.
_BUCKET_NS = 100_000_000
_CACHE_SIZE = 256
_REMOTE_PROTOCOLS = frozenset({"s3", "gs", "gcs", "http", "https"})

_SpanKey = tuple[str, str, int, int]


class _InFlight:
    """One download of a time bucket shared by the lookups that need it together."""

    def __init__(self) -> None:
        """Starts a download that has not finished."""
        self.event = threading.Event()
        self.edges: tuple[StaticTransform, ...] | None = None
        self.error: BaseException | None = None
        self.waiters = 0


_lock = threading.Lock()
_edges: OrderedDict[_SpanKey, tuple[StaticTransform, ...]] = OrderedDict()
_inflight: dict[_SpanKey, _InFlight] = {}


def caches(uri: str) -> bool:
    """Returns whether dynamic transforms at `uri` are shared across lookups.

    Args:
        uri: The path or URI of the MCAP file.

    Returns:
        `True` for a remote file. A local path is read again each time, so a test
        can rewrite it.
    """
    return fsspec.utils.get_protocol(uri) in _REMOTE_PROTOCOLS


def edges_covering(
    uri: str,
    topic: str,
    timestamp_ns: int,
    window_ns: int,
    load: Callable[[int, int], list[StaticTransform]],
) -> list[StaticTransform]:
    """Returns the dynamic edges that a lookup at `timestamp_ns` may select.

    Args:
        uri: The URI of the MCAP file.
        topic: The dynamic transform topic, e.g. `/tf`.
        timestamp_ns: The capture time of the lookup, in nanoseconds.
        window_ns: How far before and after `timestamp_ns` a transform may lie.
        load: Reads the edges whose log time is in `[start_ns, end_ns)`. Called
            once per time bucket.

    Returns:
        The edges in the bucket that covers `timestamp_ns`. The caller keeps the
        one closest to `timestamp_ns` for each child frame.

    Raises:
        Exception: The lookup that read the bucket failed. Waiting lookups raise
            the same error.
    """
    start_ns, end_ns = _covering_bounds(timestamp_ns=timestamp_ns, window_ns=window_ns)
    if not caches(uri):
        return load(start_ns, end_ns)
    key = (uri, topic, start_ns, end_ns)
    cached = _take(key)
    if cached is None:
        cached = _load_once(key=key, load=lambda: load(start_ns, end_ns))
    return list(cached)


def clear() -> None:
    """Drops cached edges and releases lookups waiting on a download."""
    with _lock:
        flights = list(_inflight.values())
        _edges.clear()
        _inflight.clear()
    for flight in flights:
        flight.event.set()


def _covering_bounds(timestamp_ns: int, window_ns: int) -> tuple[int, int]:
    """Returns the log-time span that covers every lookup in one bucket.

    Returns:
        The inclusive start and the exclusive end, in nanoseconds.
    """
    bucket_ns = timestamp_ns // _BUCKET_NS * _BUCKET_NS
    return max(bucket_ns - window_ns, 0), bucket_ns + _BUCKET_NS + window_ns


def _load_once(
    key: _SpanKey, load: Callable[[], list[StaticTransform]]
) -> tuple[StaticTransform, ...]:
    """Reads a bucket once when several lookups need it together.

    Returns:
        The edges of the bucket.

    Raises:
        Exception: The lookup that read the bucket failed.
    """
    flight, is_leader = _join(key)
    if flight is None:
        cached = _take(key)
        if cached is not None:
            return cached
        return tuple(load())
    if not is_leader:
        return _wait(flight)
    try:
        edges = tuple(load())
    except Exception as error:
        flight.error = error
        raise
    else:
        flight.edges = edges
        _store(key=key, edges=edges)
        return edges
    finally:
        _finish(key=key, flight=flight)


def _take(key: _SpanKey) -> tuple[StaticTransform, ...] | None:
    """Returns cached edges, marking them as recently used."""
    with _lock:
        edges = _edges.get(key)
        if edges is None:
            return None
        _edges.move_to_end(key)
        return edges


def _join(key: _SpanKey) -> tuple[_InFlight | None, bool]:
    """Joins the download of a bucket, or reports that the cache now holds it.

    Returns:
        The in-flight download and whether this caller reads the file. The
        download is `None` when another caller stored the edges first.
    """
    with _lock:
        if key in _edges:
            _edges.move_to_end(key)
            return None, False
        flight = _inflight.get(key)
        if flight is None:
            flight = _InFlight()
            _inflight[key] = flight
            return flight, True
        flight.waiters += 1
        return flight, False


def _wait(flight: _InFlight) -> tuple[StaticTransform, ...]:
    """Waits for the lookup that is reading a bucket.

    Returns:
        The edges of the bucket. Empty when the cache was cleared while waiting.

    Raises:
        Exception: The lookup that read the bucket failed. The same error is
            raised here.
    """
    flight.event.wait()
    if flight.error is not None:
        raise flight.error
    if flight.edges is None:
        return ()
    return flight.edges


def _finish(key: _SpanKey, flight: _InFlight) -> None:
    """Wakes the lookups waiting on a download."""
    with _lock:
        _inflight.pop(key, None)
    flight.event.set()


def _store(key: _SpanKey, edges: tuple[StaticTransform, ...]) -> None:
    """Stores a bucket and drops the least recently used ones past the bound."""
    with _lock:
        _edges[key] = edges
        _edges.move_to_end(key)
        while len(_edges) > _CACHE_SIZE:
            _edges.popitem(last=False)
