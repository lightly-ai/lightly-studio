"""Process-wide cache of video decoders, one per camera channel of a recording.

A decoder holds the state of a channel after the last frame it decoded. When the
next request asks for a later frame of the same GOP, the decoder continues from that
state, so stepping forward decodes each message once instead of decoding from the
keyframe again.

Requests run on a thread pool, and consecutive requests for a channel can run on
different threads. A decoder is not thread-safe. `borrow_decoder` holds the channel
until the request returns, so the requests of one channel run one after another and
share that decoder.
"""

from __future__ import annotations

import threading
from collections import OrderedDict
from collections.abc import Iterator
from contextlib import contextmanager

from lightly_studio.core.mcap.compressed_video import VideoDecoder
from lightly_studio.services.recording_service import camera_jpeg_cache

# The served picture is released before the decoder is stored. The codec keeps its
# reference frames, about 26 MB for a 1536x1920 H.265 camera. Thirty entries are
# about 780 MB, enough for several recordings.
_DECODER_CACHE_SIZE = 30

_guard = threading.Lock()


class _Channel:
    """The decoder of one camera channel and the lock that guards it."""

    def __init__(self) -> None:
        self.lock = threading.Lock()
        self.decoder: VideoDecoder | None = None


_channels: OrderedDict[tuple[str, int], _Channel] = OrderedDict()


class DecoderLease:
    """Exclusive access to the decoder of one camera channel.

    Attributes:
        decoder: The channel's decoder, or `None` when the channel has none.
    """

    def __init__(self, channel: _Channel) -> None:
        """Binds the lease to a channel. The caller must already hold its lock."""
        self._channel = channel

    @property
    def decoder(self) -> VideoDecoder | None:
        """The channel's decoder, or `None` when the channel has none."""
        return self._channel.decoder

    def reset(self, keyframe_log_time_ns: int) -> VideoDecoder:
        """Replaces the channel's decoder with one that starts at a keyframe.

        Args:
            keyframe_log_time_ns: The log time of the keyframe. The first message
                fed to the decoder must be this keyframe.

        Returns:
            The new decoder.
        """
        decoder = VideoDecoder(keyframe_log_time_ns=keyframe_log_time_ns)
        self._channel.decoder = decoder
        return decoder


@contextmanager
def borrow_decoder(uri: str, channel_id: int) -> Iterator[DecoderLease]:
    """Yields exclusive access to the decoder of a camera channel.

    The caller keeps the decoder when it can decode a later frame. A decoder that
    was not fed, or that failed, is dropped. Blocks until no other caller is using
    this channel. Do not call this again for the same channel from the thread that
    already holds it.

    Args:
        uri: The URI of the recording's MCAP file.
        channel_id: The camera channel of the decoder.
    """
    channel = _lock_channel(uri=uri, channel_id=channel_id)
    try:
        yield DecoderLease(channel)
    finally:
        if channel.decoder is not None and not channel.decoder.is_reusable():
            channel.decoder = None
        channel.lock.release()


def clear() -> None:
    """Removes all decoders and cached camera JPEGs."""
    with _guard:
        _channels.clear()
    camera_jpeg_cache.clear()


def _lock_channel(uri: str, channel_id: int) -> _Channel:
    """Returns the channel and holds its lock. Evicts idle channels that do not fit."""
    key = (uri, channel_id)
    with _guard:
        channel = _channels.get(key)
        if channel is None:
            channel = _Channel()
            _channels[key] = channel
        else:
            _channels.move_to_end(key)
        channel.lock.acquire()
        _evict_idle_channels()
        return channel


def _evict_idle_channels() -> None:
    """Drops the least recently used channels that no request is using."""
    overflow = len(_channels) - _DECODER_CACHE_SIZE
    if overflow <= 0:
        return
    idle = [key for key, channel in _channels.items() if not channel.lock.locked()]
    for key in idle[:overflow]:
        del _channels[key]
