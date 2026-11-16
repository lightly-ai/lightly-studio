"""The active transport that the Python API uses for all data access."""

from __future__ import annotations

from dataclasses import dataclass

from lightly_studio.database import db_manager
from lightly_studio.dataset import env
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
    """Set the active transport. None sets the default transport.

    A remote transport blocks access to the local database.
    """
    _active.transport = transport
    remote = transport is not None and not isinstance(transport, LocalTransport)
    db_manager.set_remote_client(remote=remote)


def is_remote() -> bool:
    """Return True if the active transport does not run in the process of the database."""
    return not isinstance(get_transport(), LocalTransport)


def use_transport_queries() -> bool:
    """Return True if dataset queries go through the transport instead of SQL."""
    return is_remote() or env.LIGHTLY_STUDIO_TRANSPORT_QUERIES
