"""Transport protocol for adding samples from files."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Protocol
from uuid import UUID


class IngestionTransport(Protocol):
    """Adds samples to a collection.

    A path is a local path or a cloud URI. A remote transport reads it on the server.
    """

    # TODO(Iunir, 11/2026): Add the ingestion of images and videos.
    # TODO(Iunir, 11/2026): Add MCAP ingestion when `McapComponentSpec` has no DB imports.

    def embed_images(self, collection_id: UUID, sample_ids: Sequence[UUID]) -> None:
        """Compute embeddings for images with the default embedding model of the collection.

        The images of the collection without an embedding of the default model get one too.

        Args:
            collection_id: The ID of the collection.
            sample_ids: The images to embed.
        """
