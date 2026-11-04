"""Process-wide cache of camera JPEGs, keyed by frame and output size.

A request encodes the JPEG of its target picture. A request reserves the JPEGs it
will read before it waits for the decoder, so the request that holds the decoder
also encodes a reserved picture that it decodes on the way. The waiting request
then gets the stored JPEG and does not decode the GOP again. Other pictures on the
way are not encoded.
"""

from __future__ import annotations

import threading
from collections import Counter, OrderedDict
from collections.abc import Iterable, Iterator
from contextlib import contextmanager
from dataclasses import dataclass

# A 360 px preview is a few dozen kilobytes. 1024 entries cover a prefetch window
# of several cameras.
_JPEG_CACHE_SIZE = 1024

_lock = threading.Lock()
_jpegs: OrderedDict[JpegId, bytes] = OrderedDict()
# The reserved JPEGs per picture, counted per request that reserved them.
_reserved: dict[tuple[str, int, int], Counter[JpegId]] = {}


@dataclass(frozen=True)
class JpegId:
    """One encoded camera picture.

    Attributes:
        uri: The URI of the recording's MCAP file.
        channel_id: The camera channel of the frame.
        log_time_ns: The log time of the frame, in nanoseconds.
        width: The output width in pixels, or `None` for the recorded width.
        height: The output height in pixels, or `None` for the recorded height.
        quality: The JPEG quality.
    """

    uri: str
    channel_id: int
    log_time_ns: int
    width: int | None
    height: int | None
    quality: int


def get_jpeg(jpeg_id: JpegId) -> bytes | None:
    """Returns the cached JPEG of a frame, or `None` when it is not cached.

    Args:
        jpeg_id: The frame and the output size to look up.
    """
    with _lock:
        data = _jpegs.get(jpeg_id)
        if data is not None:
            _jpegs.move_to_end(jpeg_id)
        return data


def put_jpeg(jpeg_id: JpegId, data: bytes) -> None:
    """Stores the JPEG of a frame and evicts the least recently used entries.

    Args:
        jpeg_id: The frame and the output size of `data`.
        data: The JPEG bytes.
    """
    with _lock:
        _jpegs[jpeg_id] = data
        _jpegs.move_to_end(jpeg_id)
        while len(_jpegs) > _JPEG_CACHE_SIZE:
            _jpegs.popitem(last=False)


@contextmanager
def reserve(jpeg_ids: Iterable[JpegId]) -> Iterator[None]:
    """Reserves JPEGs that the caller reads while the context is open.

    A decoder that decodes a reserved picture encodes its JPEG, see `reserved_at`.

    Args:
        jpeg_ids: The pictures and output sizes the caller will read.
    """
    reserved = list(jpeg_ids)
    with _lock:
        for jpeg_id in reserved:
            _reserved.setdefault(_picture_key(jpeg_id=jpeg_id), Counter())[jpeg_id] += 1
    try:
        yield
    finally:
        with _lock:
            for jpeg_id in reserved:
                key = _picture_key(jpeg_id=jpeg_id)
                counts = _reserved[key]
                counts[jpeg_id] -= 1
                if counts[jpeg_id] == 0:
                    del counts[jpeg_id]
                if not counts:
                    del _reserved[key]


def reserved_at(uri: str, channel_id: int, log_time_ns: int) -> list[JpegId]:
    """Returns the reserved JPEGs of one picture, one per output size.

    Args:
        uri: The URI of the recording's MCAP file.
        channel_id: The camera channel of the picture.
        log_time_ns: The log time of the picture, in nanoseconds.
    """
    with _lock:
        return list(_reserved.get((uri, channel_id, log_time_ns), ()))


def clear() -> None:
    """Removes all JPEGs from the cache."""
    with _lock:
        _jpegs.clear()


def _picture_key(jpeg_id: JpegId) -> tuple[str, int, int]:
    """Returns the picture of a JPEG without its output size."""
    return (jpeg_id.uri, jpeg_id.channel_id, jpeg_id.log_time_ns)
