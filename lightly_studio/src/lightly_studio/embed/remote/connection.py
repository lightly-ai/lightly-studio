"""Opens the connection that reaches an embedding server.

The client that carries every request to a server, and the report for a server that
answers before its model is ready. A caller opens the client, hands it to
``RemoteEmbedder.connect`` and closes it when it has no further use for the embedder.
"""

from __future__ import annotations

import logging

import httpx
from lightly_studio_serve.protocol import DescribeResponse

logger = logging.getLogger(__name__)

# The budget of a request of the client that `build_client` opens.
# TODO(Iunir, 09/2026): Replace with a budget per capability. A text query sits under a
# key press, and an image or a video needs a much higher read ceiling.
_DEFAULT_TIMEOUT_SECONDS = 30.0


def build_client(url: str) -> httpx.Client:
    """Open a client against ``url``.

    ``follow_redirects`` stays off, which is also the default of httpx. A redirect would
    carry the batch, and the bearer token with it, to an address that nobody configured.

    The caller owns the client that this returns. A client behind a registered embedder
    lives as long as the process, because ``EmbedderRegistry`` holds the embedder and
    offers no teardown.
    """
    # TODO(Iunir, 09/2026): Close the client of a registered embedder when
    # `EmbedderRegistry` gains a teardown hook.
    return httpx.Client(
        base_url=url, follow_redirects=False, timeout=httpx.Timeout(_DEFAULT_TIMEOUT_SECONDS)
    )


def log_if_loading(description: DescribeResponse, client: httpx.Client) -> None:
    """Report a server that answers before its weights arrive.

    ``connect`` succeeds either way. The embed routes answer 503 until the weights arrive,
    and the transport waits out far fewer attempts than a model load takes, so without
    this line the first search reports a busy server and names no reason.
    """
    if not description.ready:
        logger.warning(
            "The embedding server at %s reports that its model is still loading. A request "
            "that arrives before the weights do fails as if the server were busy.",
            client.base_url,
        )
