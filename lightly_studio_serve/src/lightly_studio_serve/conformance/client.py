"""What a conformance run needs from an HTTP client, and nothing more.

The interface is two methods, so LightlyStudio can run the same checks over the client it
already holds and a test can run them without opening a port.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


class ConformanceRequestError(RuntimeError):
    """A request got no answer. The message names the address and the reason."""


@dataclass(frozen=True)
class ProbeResponse:
    """What a server answered."""

    status_code: int
    body: bytes


class ProbeClient(Protocol):
    """Sends the requests of a conformance run to one server.

    An implementation adds the credentials, because the run holds no key. A status the
    server chose is a result: both methods return whatever it answered, and raise
    ``ConformanceRequestError`` only when nothing arrived.
    """

    def get(self, path: str, timeout: float) -> ProbeResponse:
        """Send a ``GET`` to ``path``, waiting at most ``timeout`` seconds."""
        ...

    def post(self, path: str, content_type: str, body: bytes, timeout: float) -> ProbeResponse:
        """Send ``body`` as ``content_type`` to ``path``, waiting at most ``timeout`` seconds."""
        ...
