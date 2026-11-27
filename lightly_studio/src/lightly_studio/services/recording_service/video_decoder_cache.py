"""Process-wide cache of video decoders, one per GOP of a camera channel.

A decoder keeps the codec state after the last message it decoded. A request for a
later frame of the same GOP continues from that state, so stepping forward decodes
each message once. Two GOPs of one channel, e.g. the end of one GOP and the start of
the next, have separate decoders.

A decoder is not thread-safe. `borrow_decoder` locks the GOP until the request
returns, so the requests of one GOP run one after another.
"""

from __future__ import annotations

import threading
from collections import OrderedDict
from collections.abc import Iterator
from contextlib import contextmanager

from lightly_studio.core.mcap.compressed_video import VideoDecoder
from lightly_studio.services.recording_service import camera_jpeg_cache

# A decoder releases each picture after it is encoded, but the codec keeps its
# reference frames, about 26 MB for a 1536x1920 H.265 camera. Thirty decoders are
# about 780 MB, enough for two GOPs of the cameras of several recordings.
_DECODER_CACHE_SIZE = 30

_guard = threading.Lock()

_GopKey = tuple[str, int, int]


class DecoderLease:
    """Exclusive access to the decoder of one GOP of a camera channel."""

    def __init__(self, gop: _Gop) -> None:
        """Binds the lease to a GOP. The caller must already hold its lock."""
        self._gop = gop

    @property
    def decoder(self) -> VideoDecoder | None:
        """The GOP's decoder, or `None` when the GOP has none."""
        return self._gop.decoder

    def reset(self) -> VideoDecoder:
        """Replaces the GOP's decoder with one that starts at its keyframe.

        Returns:
            The new decoder. The first message fed to it must be the keyframe.
        """
        decoder = VideoDecoder(keyframe_log_time_ns=self._gop.keyframe_log_time_ns)
        self._gop.decoder = decoder
        return decoder


class _Gop:
    """The decoder of one GOP of a camera channel and the lock that guards it."""

    def __init__(self, keyframe_log_time_ns: int) -> None:
        self.keyframe_log_time_ns = keyframe_log_time_ns
        self.lock = threading.Lock()
        self.decoder: VideoDecoder | None = None
        # The requests that hold or wait for the lock. Guarded by `_guard`.
        self.users = 0


_gops: OrderedDict[_GopKey, _Gop] = OrderedDict()


@contextmanager
def borrow_decoder(uri: str, channel_id: int, keyframe_log_time_ns: int) -> Iterator[DecoderLease]:
    """Yields exclusive access to the decoder of one GOP of a camera channel.

    Blocks until no other caller uses this GOP. Do not call this again for the same
    GOP from the thread that holds it. A decoder that cannot be reused, e.g. one that
    failed, is dropped on exit.

    Args:
        uri: The URI of the recording's MCAP file.
        channel_id: The camera channel of the decoder.
        keyframe_log_time_ns: The log time of the keyframe that starts the GOP.
    """
    gop = _lock_gop(key=(uri, channel_id, keyframe_log_time_ns))
    try:
        yield DecoderLease(gop=gop)
    finally:
        if gop.decoder is not None and not gop.decoder.is_reusable():
            gop.decoder = None
        gop.lock.release()
        with _guard:
            gop.users -= 1


def peek_decoder(uri: str, channel_id: int, keyframe_log_time_ns: int) -> VideoDecoder | None:
    """Returns the decoder of one GOP of a camera channel without borrowing it.

    Another request can feed or replace the decoder at any time. Use the result only
    as a hint and do not feed it.

    Args:
        uri: The URI of the recording's MCAP file.
        channel_id: The camera channel of the decoder.
        keyframe_log_time_ns: The log time of the keyframe that starts the GOP.

    Returns:
        The GOP's decoder, or `None` when the GOP has none.
    """
    with _guard:
        gop = _gops.get((uri, channel_id, keyframe_log_time_ns))
    return None if gop is None else gop.decoder


def clear() -> None:
    """Removes all decoders and cached camera JPEGs."""
    with _guard:
        _gops.clear()
    camera_jpeg_cache.clear()


def _lock_gop(key: _GopKey) -> _Gop:
    """Returns the GOP and holds its lock. Evicts idle GOPs that do not fit."""
    with _guard:
        gop = _gops.get(key)
        if gop is None:
            gop = _Gop(keyframe_log_time_ns=key[2])
            _gops[key] = gop
        else:
            _gops.move_to_end(key)
        gop.users += 1
        _evict_idle_gops()
    # Lock outside the guard, so a request that waits for a busy GOP does not block
    # other GOPs. The user count keeps the GOP in the cache.
    gop.lock.acquire()
    return gop


def _evict_idle_gops() -> None:
    """Drops the least recently used GOPs that no request is using or waiting for."""
    overflow = len(_gops) - _DECODER_CACHE_SIZE
    if overflow <= 0:
        return
    idle = [key for key, gop in _gops.items() if gop.users == 0]
    for key in idle[:overflow]:
        del _gops[key]
