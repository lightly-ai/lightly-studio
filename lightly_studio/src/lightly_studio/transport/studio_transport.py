"""The transport that the Python API uses for all data access."""

from __future__ import annotations

from typing import Protocol

from lightly_studio.transport.collection_transport import CollectionTransport


class StudioTransport(Protocol):
    """Groups the transports for each area of the Python API.

    `LocalTransport` runs in the same process as the database. An HTTP transport will call
    the Studio backend.
    """

    @property
    def collections(self) -> CollectionTransport:
        """The transport for collections."""
