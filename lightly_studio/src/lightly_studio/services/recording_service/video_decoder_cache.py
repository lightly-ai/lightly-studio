"""Process-wide cache of video decoders, one per camera channel of a recording.

A decoder holds the state of a channel after the last frame it decoded. When the
next request asks for a later frame of the same GOP, the decoder continues from that
state, so stepping forward decodes each message once instead of decoding from the
keyframe again.

Requests run on a thread pool, and consecutive requests for a channel can run on
different threads, so the cache is shared between threads. A decoder is not
thread-safe: `take_decoder` removes it from the cache, so only one request uses it,
and `put_decoder` returns it when the request is done.
"""

from __future__ import annotations

import threading
from collections import OrderedDict

from lightly_studio.core.mcap.compressed_video import VideoDecoder

# The served picture is released before the decoder is stored. The codec keeps its
# reference frames, about 26 MB for a 1536x1920 H.265 camera. Thirty entries are
# about 780 MB, enough for several recordings.
_DECODER_CACHE_SIZE = 30

_lock = threading.Lock()
_decoders: OrderedDict[tuple[str, int], VideoDecoder] = OrderedDict()


def take_decoder(uri: str, channel_id: int) -> VideoDecoder | None:
    """Removes the decoder of a channel from the cache and returns it.

    The caller owns the decoder until it returns it with `put_decoder`.

    Args:
        uri: The URI of the recording's MCAP file.
        channel_id: The camera channel of the decoder.

    Returns:
        The cached decoder, or `None` if the channel has no cached decoder.
    """
    with _lock:
        return _decoders.pop((uri, channel_id), None)


def put_decoder(uri: str, channel_id: int, decoder: VideoDecoder) -> None:
    """Stores the decoder of a channel, and evicts the least recently stored decoders.

    Replaces a decoder that another request stored for the same channel meanwhile.

    Args:
        uri: The URI of the recording's MCAP file.
        channel_id: The camera channel of the decoder.
        decoder: The decoder to store.
    """
    with _lock:
        _decoders[(uri, channel_id)] = decoder
        _decoders.move_to_end((uri, channel_id))
        while len(_decoders) > _DECODER_CACHE_SIZE:
            _decoders.popitem(last=False)


def clear() -> None:
    """Removes all decoders from the cache."""
    with _lock:
        _decoders.clear()
