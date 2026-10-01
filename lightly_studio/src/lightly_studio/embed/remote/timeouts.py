"""Holds the time budget that each capability of the embedding protocol gets.

One budget for every call is wrong in both directions. A text query answers while a user
waits on it, so a high ceiling turns a broken server into a hang. A batch of encoded
videos needs far longer than that, and the same low ceiling would fail on a server that is
working correctly.

Every value is a budget of httpx, which limits one phase of a request and not the call as
a whole. ``RemoteTransport`` puts the budget of the capability on each request it sends.
"""

from __future__ import annotations

from dataclasses import dataclass

import httpx

# The time to open a connection, the same for every request. A server that does not accept
# a connection inside it is down, whatever the request was going to carry.
_CONNECT_SECONDS = 3.0

# The time to wait for a free connection of the pool. A request waits here only while the
# pool is full, which says nothing about the server, so the wait follows the budget of the
# capability: a caller that accepts a long answer also accepts a wait for its turn.

# `/v1/describe` carries no payload, and it runs at construction with
# `EmbedderRegistry.register` waiting on it.
_DESCRIBE_READ_SECONDS = 10.0

# A text query sits under the Enter key of a user in the GUI. A single answer that takes
# longer than this is a hang, not a slow answer. A retried query still waits out one
# budget per attempt, so this is not a ceiling on the whole call.
_TEXT_READ_SECONDS = 10.0

# A batch of encoded images. The server decodes each one and runs a forward pass over it.
_IMAGE_BYTES_READ_SECONDS = 120.0

# A batch of encoded videos. Decoding a video is the most expensive work that a server of
# this protocol does.
_VIDEO_BYTES_READ_SECONDS = 300.0


@dataclass(frozen=True)
class RemoteTimeouts:
    """The budget of one request, per capability.

    One budget for every call is wrong in both directions. A text query answers while a
    user waits on it, so a high ceiling turns a broken server into a hang. A batch of
    encoded videos needs far longer than that, and the same low ceiling would fail on a
    server that is working correctly.

    Each field carries the connect, read, write and pool budget of the requests of one
    capability. ``DEFAULT_TIMEOUTS`` holds the values that this client applies, and
    ``dataclasses.replace`` changes one of them.

    Attributes:
        describe: The budget of ``GET /v1/describe``.
        text: The budget of ``POST /v1/embed/texts``.
        image_bytes: The budget of ``POST /v1/embed/images/bytes``.
        video_bytes: The budget of ``POST /v1/embed/videos/bytes``.
    """

    describe: httpx.Timeout
    text: httpx.Timeout
    image_bytes: httpx.Timeout
    video_bytes: httpx.Timeout


def _budget(read_seconds: float) -> httpx.Timeout:
    """Build the budget of one capability out of its read budget.

    The write and pool budgets follow the read budget. Sending a batch of encoded items
    over a slow link is a write and not a read, and a request that waits for a free
    connection of the pool waits on the other requests of this client, not on the server.

    Each of these limits one phase of a request. httpx reads the answer in chunks and
    applies the read budget to the wait for one chunk, so a server that keeps sending can
    hold a request for longer than the budget names.

    Args:
        read_seconds: The time to wait for one chunk of the answer of the server.

    Returns:
        The budget to put on a request of the capability.
    """
    return httpx.Timeout(
        connect=_CONNECT_SECONDS,
        read=read_seconds,
        write=read_seconds,
        pool=read_seconds,
    )


DEFAULT_TIMEOUTS = RemoteTimeouts(
    describe=_budget(_DESCRIBE_READ_SECONDS),
    text=_budget(_TEXT_READ_SECONDS),
    image_bytes=_budget(_IMAGE_BYTES_READ_SECONDS),
    video_bytes=_budget(_VIDEO_BYTES_READ_SECONDS),
)
