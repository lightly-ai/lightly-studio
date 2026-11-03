"""The transport that the Python API uses for all data access."""

from __future__ import annotations

from typing import Protocol

from lightly_studio.transport.collection_transport import CollectionTransport
from lightly_studio.transport.local.local_transport import LocalTransport


class StudioTransport(Protocol):
    """Groups the transports for each area of the Python API.

    `LocalTransport` runs in the same process as the database. An HTTP transport will call
    the Studio backend.
    """

    @property
    def collections(self) -> CollectionTransport:
        """The transport for collections."""


_transport: StudioTransport | None = None


def get_transport() -> StudioTransport:
    """Get the active transport. If no transport is set, set a `LocalTransport`."""
    global _transport  # noqa: PLW0603
    if _transport is None:
        _transport = LocalTransport()
    return _transport


def set_transport(transport: StudioTransport) -> None:
    """Set the active transport."""
    global _transport  # noqa: PLW0603
    _transport = transport
