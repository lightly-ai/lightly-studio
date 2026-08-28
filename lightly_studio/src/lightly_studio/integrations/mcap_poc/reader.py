"""Indexed MCAP access and benchmark measurements for the processing PoC."""

from __future__ import annotations

import contextlib
import threading
import time
import tracemalloc
from collections.abc import Callable, Generator
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Any, BinaryIO, cast
from urllib import parse

import fsspec
from mcap import reader as mcap_reader
from mcap_ros2.decoder import DecoderFactory

from lightly_studio.integrations.mcap_poc import point_cloud

_BENCHMARK_LOCK = threading.Lock()

# Keeping the parsed summary alive between requests is the whole point of the comparison: on a
# ~900 MB recording, parsing the chunk index costs about ten times more than reading and decoding
# the frame itself. The browser path amortises the same work inside one long-lived reader.
_OPEN_SOURCES: dict[str, _OpenSource] = {}


@dataclass(frozen=True)
class McapTopic:
    """Point-cloud topic metadata."""

    topic: str
    message_count: int
    first_log_time_ns: int


@dataclass(frozen=True)
class McapSourceDescription:
    """Metadata required to benchmark a fixed MCAP source."""

    size_bytes: int
    version: str
    topics: list[McapTopic]


@dataclass(frozen=True)
class McapFrameResult:
    """Render-ready point frame and benchmark measurements."""

    content: bytes
    point_count: int
    log_time_ns: int
    bytes_read: int
    read_count: int
    wall_time_ms: float
    index_time_ms: float
    decode_time_ms: float
    cpu_time_ms: float
    peak_memory_bytes: int
    index_cached: bool


class _CountingReader:
    def __init__(self, stream: BinaryIO) -> None:
        self._stream = stream
        self.bytes_read = 0
        self.read_count = 0

    def reset_counts(self) -> None:
        self.bytes_read = 0
        self.read_count = 0

    def read(self, size: int = -1) -> bytes:
        data = self._stream.read(size)
        self.bytes_read += len(data)
        self.read_count += 1
        return data

    def seek(self, offset: int, whence: int = 0) -> int:
        return self._stream.seek(offset, whence)

    def tell(self) -> int:
        return self._stream.tell()

    def seekable(self) -> bool:
        return self._stream.seekable()


@dataclass
class _OpenSource:
    """An MCAP source whose summary index has already been parsed."""

    version: str
    size_bytes: int
    counting: _CountingReader
    reader: Any
    summary: Any
    close: Callable[[], None]


def describe_source(source: str) -> McapSourceDescription:
    """Describe indexed PointCloud2 topics in an MCAP source.

    Args:
        source: Local path or HTTP(S)/object-store URL of the MCAP recording.

    Returns:
        The source size, a cache-validating version token, and its PointCloud2 topics.
    """
    with _BENCHMARK_LOCK:
        opened = _acquire(source=source, reuse_index=True)[0]
        topics = _point_cloud_topics(reader=opened.reader, summary=opened.summary)
        if not topics:
            raise ValueError("The MCAP source has no ROS 2 PointCloud2 topics.")
        return McapSourceDescription(
            size_bytes=opened.size_bytes, version=opened.version, topics=topics
        )


def read_point_cloud_frame(
    source: str, topic: str, timestamp_ns: int, reuse_index: bool = True
) -> McapFrameResult:
    """Read the first point-cloud frame at or after a timestamp.

    Args:
        source: Local path or HTTP(S)/object-store URL of the MCAP recording.
        topic: ROS 2 PointCloud2 topic to read.
        timestamp_ns: Nanosecond log time to seek to.
        reuse_index: Reuse a previously parsed summary index. Pass ``False`` to measure the
            cold cost of opening and indexing the source on every request.

    Returns:
        The packed float32 XYZI frame together with its benchmark measurements.
    """
    with _BENCHMARK_LOCK:
        return _read_point_cloud_frame(
            source=source, topic=topic, timestamp_ns=timestamp_ns, reuse_index=reuse_index
        )


def clear_source_cache() -> None:
    """Close and forget every cached MCAP source."""
    with _BENCHMARK_LOCK:
        _clear_open_sources()


def local_source_path(source: str) -> Path | None:
    """Return a local source path, or None for remote sources.

    Args:
        source: Configured MCAP source.

    Returns:
        The resolved local path, or ``None`` when the source is remote.
    """
    parsed = parse.urlparse(source)
    if parsed.scheme not in ("", "file"):
        return None
    path = Path(parsed.path if parsed.scheme == "file" else source).expanduser().resolve()
    if not path.is_file():
        raise ValueError(f"Configured MCAP source does not exist: {path}")
    return path


def _read_point_cloud_frame(
    source: str, topic: str, timestamp_ns: int, reuse_index: bool
) -> McapFrameResult:
    wall_start = time.perf_counter()
    cpu_start = time.process_time()
    tracemalloc.start()
    try:
        opened, index_cached = _acquire(source=source, reuse_index=reuse_index)
        index_time_ms = (time.perf_counter() - wall_start) * 1000
        opened.counting.reset_counts()
        decode_start = time.perf_counter()
        content, log_time_ns = _decode_frame(opened=opened, topic=topic, timestamp_ns=timestamp_ns)
        decode_time_ms = (time.perf_counter() - decode_start) * 1000
        _, peak_memory_bytes = tracemalloc.get_traced_memory()
    finally:
        tracemalloc.stop()
    return McapFrameResult(
        content=content,
        point_count=len(content) // 16,
        log_time_ns=log_time_ns,
        bytes_read=opened.counting.bytes_read,
        read_count=opened.counting.read_count,
        wall_time_ms=(time.perf_counter() - wall_start) * 1000,
        index_time_ms=0.0 if index_cached else index_time_ms,
        decode_time_ms=decode_time_ms,
        cpu_time_ms=(time.process_time() - cpu_start) * 1000,
        peak_memory_bytes=peak_memory_bytes,
        index_cached=index_cached,
    )


def _decode_frame(opened: _OpenSource, topic: str, timestamp_ns: int) -> tuple[bytes, int]:
    messages = opened.reader.iter_decoded_messages(topics=[topic], start_time=timestamp_ns)
    try:
        _, _, message, decoded = next(messages)
    except StopIteration as error:
        raise ValueError(f"No message found for topic '{topic}' at {timestamp_ns} ns.") from error
    points = point_cloud.decode_point_cloud2(message=decoded)
    return points.astype("<f4", copy=False).tobytes(), message.log_time


def _acquire(source: str, reuse_index: bool) -> tuple[_OpenSource, bool]:
    cached = _OPEN_SOURCES.get(source)
    if cached is not None and (not reuse_index or _is_stale(source=source, cached=cached)):
        _close_open_source(source=source)
        cached = None
    if cached is not None:
        return cached, True
    opened = _open_indexed(source=source, version=_source_version(source=source))
    if reuse_index:
        _OPEN_SOURCES[source] = opened
    return opened, False


def _is_stale(source: str, cached: _OpenSource) -> bool:
    """Report whether a cached source was replaced on disk.

    Remote sources are never re-validated: re-opening the object only to read its ETag would
    add a request to every frame and defeat the caching this PoC is measuring.
    """
    if local_source_path(source=source) is None:
        return False
    return cached.version != _source_version(source=source)


def _open_indexed(source: str, version: str) -> _OpenSource:
    stream, close = _open_stream(source=source)
    try:
        counting = _CountingReader(stream=stream)
        reader = mcap_reader.make_reader(
            cast(BinaryIO, counting), decoder_factories=[DecoderFactory()]
        )
        summary = reader.get_summary()
        if summary is None:
            raise ValueError("The MCAP source has no readable summary index.")
    except Exception:
        close()
        raise
    return _OpenSource(
        version=version,
        size_bytes=_stream_size(stream=stream),
        counting=counting,
        reader=reader,
        summary=summary,
        close=close,
    )


def _point_cloud_topics(reader: Any, summary: Any) -> list[McapTopic]:
    result = []
    counts = summary.statistics.channel_message_counts if summary.statistics else {}
    for channel in summary.channels.values():
        schema = summary.schemas.get(channel.schema_id)
        if schema is None or not schema.name.endswith("PointCloud2"):
            continue
        first = next(reader.iter_messages(topics=[channel.topic]), None)
        if first is None:
            continue
        result.append(
            McapTopic(
                topic=channel.topic,
                message_count=int(counts.get(channel.id, 0)),
                first_log_time_ns=first[2].log_time,
            )
        )
    return sorted(result, key=lambda item: item.topic)


def _open_stream(source: str) -> tuple[BinaryIO, Callable[[], None]]:
    path = local_source_path(source=source)
    if path is not None:
        handle = path.open("rb")
        return handle, handle.close
    remote = fsspec.open(source, mode="rb")
    stream = cast(BinaryIO, remote.open())
    return stream, remote.close


@contextmanager
def _open_source(source: str) -> Generator[BinaryIO, None, None]:
    stream, close = _open_stream(source=source)
    try:
        yield stream
    finally:
        close()


def _clear_open_sources() -> None:
    for source in list(_OPEN_SOURCES):
        _close_open_source(source=source)


def _close_open_source(source: str) -> None:
    opened = _OPEN_SOURCES.pop(source, None)
    if opened is None:
        return
    with contextlib.suppress(OSError):
        opened.close()


def _stream_size(stream: BinaryIO) -> int:
    position = stream.tell()
    stream.seek(0, 2)
    size = stream.tell()
    stream.seek(position)
    return size


def _source_version(source: str) -> str:
    path = local_source_path(source=source)
    if path is not None:
        stat = path.stat()
        return f"{stat.st_mtime_ns:x}-{stat.st_size:x}"
    with _open_source(source=source) as stream:
        details = getattr(stream, "details", {})
        return str(
            details.get("ETag")
            or details.get("etag")
            or details.get("version_id")
            or _stream_size(stream=stream)
        )
