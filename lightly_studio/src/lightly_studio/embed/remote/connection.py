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


def build_client(url: str) -> httpx.Client:
    """Open a client against ``url``.

    ``follow_redirects`` stays off, which is also the default of httpx. It is written out
    because it is a control and not a preference: a redirect would carry the batch, and
    the bearer token with it, to an address that nobody configured.
    ``url_policy.check_no_redirects`` then checks the value, here and for a client that a
    caller passes in.

    The budget of the client stays at the default of httpx, and ``RemoteTransport``
    overrides it on every request it sends: the right ceiling depends on what a request
    carries, so the budget of the capability comes from ``RemoteTimeouts``.

    The caller owns the client that this returns. A client behind a registered embedder
    lives as long as the process, because ``EmbedderRegistry`` holds the embedder and
    offers no teardown.
    """
    # TODO(Iunir, 09/2026): Close the client of a registered embedder when
    # `EmbedderRegistry` gains a teardown hook.
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
