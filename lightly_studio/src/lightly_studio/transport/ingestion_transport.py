"""Transport protocol for adding samples from files."""

from __future__ import annotations

from typing import Protocol


class IngestionTransport(Protocol):
    """Adds images and videos to a collection.

    A path is a local path or a cloud URI. A remote transport reads it on the server.
    """

    # TODO(Iunir, 11/2026): Add image and video ingestion with the local implementation.
    # TODO(Iunir, 11/2026): Add MCAP ingestion when `McapComponentSpec` has no DB imports.
