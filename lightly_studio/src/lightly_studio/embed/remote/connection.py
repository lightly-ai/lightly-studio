"""Opens the connection that reaches an embedding server.

What ``RemoteEmbedder.connect`` sets up before it builds the embedder: the client that
carries every request, and the report for a server that answers before its model is ready.
"""

from __future__ import annotations

import logging

import httpx
from lightly_studio_serve.protocol import DescribeResponse

logger = logging.getLogger(__name__)


def build_client(url: str) -> httpx.Client:
    """Open a client against ``url``.

    ``follow_redirects`` stays off, which is also the default of httpx. A redirect would
    carry the batch, and the bearer token with it, to an address that nobody configured.

    The client carries no budget of its own. The right ceiling depends on what a request
    carries, so ``RemoteTransport`` puts the budget of the capability on each request, out
    of ``RemoteTimeouts``.

    The embedder owns this client and closes it in ``RemoteEmbedder.close``. A registered
    embedder is never closed, because ``EmbedderRegistry`` holds it for the lifetime of the
    process and offers no teardown, so its pool lives as long as the process does.
    """
    # TODO(Iunir, 09/2026): Close a registered embedder when `EmbedderRegistry` gains a
    # teardown hook.
    return httpx.Client(base_url=url, follow_redirects=False)


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
