"""Errors raised when resolving an embedder for a collection."""

from __future__ import annotations

from lightly_studio_serve.embedder import Embedder


class NoUsableEmbedderError(Exception):
    """Raised when samples need an embedding and no embedder is available for them."""


class QueryEmbedderError(ValueError):
    """Raised when no embedder can answer a query for a collection."""


class NoDefaultEmbeddingModelError(QueryEmbedderError):
    """Raised when a query targets a collection with no default embedding model."""


class MissingCapabilityError(QueryEmbedderError):
    """Raised when no embedder of the default embedding space has the queried capability."""

    def __init__(self, space_key: str, embedder_type: type[Embedder]) -> None:
        """Create the error for a space with no embedder of ``embedder_type``."""
        super().__init__(f"The embedding space {space_key!r} has no {embedder_type.__name__}.")


class RemoteEmbedderUnavailableError(QueryEmbedderError):
    """Raised when the embedding server of the default embedding space cannot be used.

    The server is unreachable, rejects the token, or fails the identity check.
    """

    def __init__(self, space_key: str, url: str) -> None:
        """Create the error for the server at ``url`` that serves ``space_key``."""
        super().__init__(
            f"The embedding server at {url!r} for the embedding space {space_key!r} cannot be used."
        )
