"""The active transport that the Python API uses for all data access."""

from __future__ import annotations

from dataclasses import dataclass

from lightly_studio.transport.local.local_transport import LocalTransport
from lightly_studio.transport.studio_transport import StudioTransport


@dataclass
class _ActiveTransport:
    """Holds the transport that `get_transport` returns. None means the default."""

    transport: StudioTransport | None = None


_active = _ActiveTransport()


def get_transport() -> StudioTransport:
    """Get the active transport. The default is a `LocalTransport`."""
    if _active.transport is None:
        _active.transport = LocalTransport()
    return _active.transport


def set_transport(transport: StudioTransport | None) -> None:
    """Set the active transport. None sets the default transport."""
    _active.transport = transport
