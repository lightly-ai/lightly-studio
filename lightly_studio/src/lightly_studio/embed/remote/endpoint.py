"""The address and the token that reach an embedding server.

A dataset stores them on the ``embedding_model`` row of a space. A later process then builds
the embedder of that space from the row, with no registration.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol, runtime_checkable


@dataclass(frozen=True)
class RemoteEndpoint:
    """The address and the token of an embedding server.

    Attributes:
        url: The base URL of the server.
        api_key: The bearer token of the server, or None if the server needs none. Kept out
            of a repr.
    """

    url: str
    api_key: str | None = field(repr=False)


@runtime_checkable
class PersistableEmbedder(Protocol):
    """An embedder that names the server it calls, so that a dataset can store the server."""

    def remote_endpoint(self) -> RemoteEndpoint | None:
        """Get the endpoint of the server that the embedder calls.

        Returns:
            The endpoint, or None if the embedder calls no server that a later process can
            reach again.
        """
        ...
