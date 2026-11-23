"""Ingestion transport that calls the v1 REST API."""

from __future__ import annotations

from collections.abc import Sequence
from uuid import UUID

import httpx


class HttpIngestionTransport:
    """Implements `IngestionTransport` over HTTP. The v1 API has no ingestion routes yet."""

    def __init__(self, client: httpx.Client) -> None:
        """Create the transport with an HTTP client for the Studio backend."""
        self._client = client

    def add_images_from_path(  # noqa: PLR0913
        self,
        collection_id: UUID,
        path: str,
        allowed_extensions: Sequence[str] | None,
        embed: bool,
        tag_depth: int,
        limit: int | None,
    ) -> None:
        """Add the raw images from a path to a collection. Not supported over HTTP yet."""
        raise NotImplementedError("Adding images over HTTP is not supported yet.")

    def embed_images(self, collection_id: UUID, sample_ids: Sequence[UUID]) -> None:
        """Compute embeddings for images. Not supported over HTTP yet."""
        raise NotImplementedError("Embedding images over HTTP is not supported yet.")
