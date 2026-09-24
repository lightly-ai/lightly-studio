"""Errors raised when resolving an embedder for a collection."""

from __future__ import annotations


class NoDefaultEmbeddingModelError(ValueError):
    """Raised when a query targets a collection with no default embedding model."""


class MissingCapabilityError(ValueError):
    """Raised when no embedder of the default embedding space has the queried capability.

    Attributes:
        space_key: The default embedding space of the collection.
    """

    def __init__(self, space_key: str) -> None:
        """Create the error for the embedding space ``space_key``."""
        super().__init__(
            f"No embedder resolves for the collection's default embedding space {space_key!r}."
        )
        self.space_key = space_key


class RemoteEmbedderUnavailableError(ValueError):
    """Raised when the embedding server of the default embedding space cannot be used.

    The server is unreachable, rejects the token, or fails the identity check.

    Attributes:
        space_key: The default embedding space of the collection.
    """

    def __init__(self, space_key: str, url: str) -> None:
        """Create the error for the server at ``url`` that serves ``space_key``."""
        super().__init__(
            f"The embedding server at {url!r} for the embedding space {space_key!r} cannot be used."
        )
        self.space_key = space_key
