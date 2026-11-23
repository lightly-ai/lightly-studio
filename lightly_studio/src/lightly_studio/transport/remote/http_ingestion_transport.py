"""Ingestion transport that calls the v1 REST API."""

from __future__ import annotations

from collections.abc import Sequence
from uuid import UUID

import httpx

from lightly_studio.models.image import AddImagesResult, ImageCreate


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

    def add_images(self, collection_id: UUID, images: Sequence[ImageCreate]) -> AddImagesResult:
        """Add images with known dimensions to a collection. Not supported over HTTP yet."""
        raise NotImplementedError("Adding images over HTTP is not supported yet.")

    def add_directory_tags(
        self, collection_id: UUID, path: str, sample_ids: Sequence[UUID], tag_depth: int
    ) -> None:
        """Tag images with the names of their folders. Not supported over HTTP yet."""
        raise NotImplementedError("Adding directory tags over HTTP is not supported yet.")

    def embed_images(self, collection_id: UUID, sample_ids: Sequence[UUID]) -> None:
        """Compute embeddings for images. Not supported over HTTP yet."""
        raise NotImplementedError("Embedding images over HTTP is not supported yet.")

    def embed_videos(self, collection_id: UUID, sample_ids: Sequence[UUID]) -> None:
        """Compute embeddings for videos. Not supported over HTTP yet."""
        raise NotImplementedError("Embedding videos over HTTP is not supported yet.")
