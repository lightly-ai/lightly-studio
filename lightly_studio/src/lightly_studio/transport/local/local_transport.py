"""Transport that calls the resolvers in the same process."""

from __future__ import annotations

from lightly_studio.transport.local.local_collection_transport import LocalCollectionTransport


class LocalTransport:
    """Implements `StudioTransport` against the database of `db_manager`."""

    def __init__(self) -> None:
        """Create the transports for each area."""
        self.collections = LocalCollectionTransport()
