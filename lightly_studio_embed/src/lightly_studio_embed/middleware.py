"""ASGI middleware that guards a request before FastAPI parses its body.

Neither check can be a dependency: FastAPI reads and parses the whole body before
it solves dependencies, so as dependencies both would arrive after an untrusted
peer had already decided how much the server buffers.
"""

from __future__ import annotations

import secrets

from fastapi import HTTPException, status
from fastapi.responses import JSONResponse
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from lightly_studio_embed import protocol


class BearerAuth:
    """Rejects a request whose bearer token is missing or wrong.

    The header is compared as the raw bytes the client sent. Decoding it first would
    make a single non-ASCII byte, in the header or in the key, raise inside
    ``secrets.compare_digest`` and answer 500 where the protocol wants 401.
    """

    def __init__(self, app: ASGIApp, *, api_key: str | None) -> None:
        """Guard ``app``, or let every request through when ``api_key`` is ``None``."""
        self.app = app
        self.expected = None if api_key is None else f"Bearer {api_key}".encode()

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        """Answer 401 for a bad token, otherwise hand the request on."""
        if self.expected is None or scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        if not secrets.compare_digest(_authorization_header(scope=scope), self.expected):
            await _unauthorized()(scope, receive, send)
            return
        await self.app(scope, receive, send)


class RequestSizeLimit:
    """Rejects a body that grows past the advertised ceiling while it arrives.

    ``Content-Length`` is not enough on its own: an HTTP/1.1 client may leave it out
    and stream the body chunked, which is the shape the ceiling most needs to bound,
    since starlette spools every multipart part over 1 MiB to disk.
    """

    def __init__(self, app: ASGIApp, *, max_request_bytes: int) -> None:
        """Guard ``app``, rejecting a body over ``max_request_bytes``."""
        self.app = app
        self.max_request_bytes = max_request_bytes

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        """Hand the request on with its body counted as it is read."""
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        await self.app(scope, self._counted(receive=receive), send)

    def _counted(self, *, receive: Receive) -> Receive:
        """Wrap ``receive`` so the body is measured as the server hands it over."""
        received = 0

        async def receive_counted() -> Message:
            nonlocal received
            message = await receive()
            if message["type"] == "http.request":
                received += len(message.get("body", b""))
                if received > self.max_request_bytes:
                    # Raised through the route into FastAPI's own handler for it.
                    raise HTTPException(
                        status_code=protocol.STATUS_PAYLOAD_TOO_LARGE,
                        detail="The request body is over the advertised max_request_bytes of "
                        f"{self.max_request_bytes}.",
                    )
            return message

        return receive_counted


def _authorization_header(*, scope: Scope) -> bytes:
    """Read the raw ``Authorization`` header. ASGI lowercases the names for us."""
    for name, value in scope["headers"]:
        if name == b"authorization":
            return bytes(value)
    return b""


def _unauthorized() -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_401_UNAUTHORIZED,
        content={"detail": "Missing or invalid bearer token."},
        headers={"WWW-Authenticate": "Bearer"},
    )
