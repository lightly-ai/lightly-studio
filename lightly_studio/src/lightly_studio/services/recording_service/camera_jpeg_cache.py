"""Process-wide cache of camera JPEGs, keyed by frame and output size.

A request stores the JPEG of each picture it decodes on the way to its target.
Another request for one of those pictures, also one that waits for the decoder,
gets the stored JPEG and does not decode the GOP again.
"""

from __future__ import annotations

import threading
from collections import OrderedDict
from dataclasses import dataclass

# A 360 px preview is a few dozen kilobytes. 1024 entries cover a prefetch window
# of several cameras, including the frames decoded between ticks.
_JPEG_CACHE_SIZE = 1024

_lock = threading.Lock()
_jpegs: OrderedDict[JpegId, bytes] = OrderedDict()


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


def clear() -> None:
    """Removes all JPEGs from the cache."""
    with _lock:
        _jpegs.clear()
