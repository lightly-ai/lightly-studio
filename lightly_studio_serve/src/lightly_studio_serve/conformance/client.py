"""What a conformance run needs from an HTTP client, and nothing more.

The interface is two methods, so LightlyStudio can run the same checks over the client it
already holds and a test can run them without opening a port. ``HttpProbeClient`` is the
one the command line uses.
"""

from __future__ import annotations

import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Protocol

# The most of an answer the client reads. The address is one a person pasted.
MAX_RESPONSE_BYTES = 8 * 1024 * 1024


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


class HttpProbeClient:
    """Sends the probes with the standard library, so the kit adds no client package.

    The opener carries neither a redirect handler nor an error processor, so a 302 and a
    401 come back as the answers they are. Following a redirect would send the bearer
    token to an address nobody typed.
    """

    def __init__(self, base_url: str, api_key: str | None = None) -> None:
        """Send to the server at ``base_url``.

        Args:
            base_url: The address of the server, such as ``http://127.0.0.1:8080``.
            api_key: The token to send as ``Authorization: Bearer <api_key>``. ``None``
                sends no header, which is what a server without a key expects.

        Raises:
            ValueError: If ``base_url`` names no HTTP address. The opener handles those
                two schemes alone, and answers nothing at all for any other.
        """
        if not base_url.startswith(("http://", "https://")):
            raise ValueError(f"base_url must start with http:// or https://, got {base_url!r}.")
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self._opener = urllib.request.OpenerDirector()
        self._opener.add_handler(urllib.request.HTTPHandler())
        self._opener.add_handler(urllib.request.HTTPSHandler())

    def get(self, path: str, timeout: float) -> ProbeResponse:
        """Send a ``GET`` to ``path``. See ``ProbeClient``."""
        request = urllib.request.Request(url=f"{self.base_url}{path}", method="GET")
        return self._send(request=request, timeout=timeout)

    def post(self, path: str, content_type: str, body: bytes, timeout: float) -> ProbeResponse:
        """Send a ``POST`` to ``path``. See ``ProbeClient``."""
        request = urllib.request.Request(url=f"{self.base_url}{path}", data=body, method="POST")
        request.add_header("Content-Type", content_type)
        return self._send(request=request, timeout=timeout)

    def _send(self, request: urllib.request.Request, timeout: float) -> ProbeResponse:
        """Send one request, and read at most the bytes an answer of the protocol needs."""
        if self.api_key is not None:
            request.add_header("Authorization", f"Bearer {self.api_key}")
        try:
            with self._opener.open(request, timeout=timeout) as response:
                status, body = response.status, response.read(MAX_RESPONSE_BYTES + 1)
        # A URLError is an OSError, and so is a read that ran out of time.
        except OSError as error:
            raise ConformanceRequestError(f"{request.full_url} got no answer: {error}.") from error
        if len(body) > MAX_RESPONSE_BYTES:
            raise ConformanceRequestError(
                f"{request.full_url} answers over {MAX_RESPONSE_BYTES} bytes. One probe "
                f"carries one item, so no answer of the protocol is that large."
            )
        return ProbeResponse(status_code=status, body=body)
