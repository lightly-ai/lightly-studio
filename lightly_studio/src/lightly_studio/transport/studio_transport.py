"""The transport that the Python API uses for all data access."""

from __future__ import annotations

from dataclasses import dataclass
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


@dataclass
class _ActiveTransport:
    """Holds the transport that `get_transport` returns."""

    transport: StudioTransport


_active = _ActiveTransport(transport=LocalTransport())


def get_transport() -> StudioTransport:
    """Get the active transport. The default is a `LocalTransport`."""
    return _active.transport


def set_transport(transport: StudioTransport) -> None:
    """Set the active transport."""
    _active.transport = transport
