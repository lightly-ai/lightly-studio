"""The transport that the Python API uses for all data access."""

from __future__ import annotations

from dataclasses import dataclass
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


@dataclass
class _ActiveTransport:
    """Holds the transport that `get_transport` returns. None means the default."""

    transport: StudioTransport | None = None


_active = _ActiveTransport()


def get_transport() -> StudioTransport:
    """Get the active transport. The default is a `LocalTransport`."""
    if _active.transport is None:
        # Import here, so that a remote client can use the protocols without the database.
        from lightly_studio.transport.local.local_transport import (  # noqa: PLC0415
            LocalTransport,
        )

        _active.transport = LocalTransport()
    return _active.transport


def set_transport(transport: StudioTransport | None) -> None:
    """Set the active transport. None sets the default transport."""
    _active.transport = transport
