"""ASGI middleware that checks a request before FastAPI reads its body.

Neither check can be a dependency. FastAPI reads the full body before it solves the
dependencies. A dependency therefore runs after an unknown peer sets how much memory
the server holds.
"""

from __future__ import annotations

import secrets

from fastapi import HTTPException, status
from fastapi.responses import JSONResponse
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from lightly_studio_embed import protocol


class BearerAuth:
    """Rejects a request with a missing or wrong bearer token.

    The class compares the raw bytes that the client sent. It does not decode the header
    first. One byte that is not ASCII raises an error inside ``secrets.compare_digest``,
    and the server then answers 500. The protocol needs 401.
    """

    def __init__(self, app: ASGIApp, *, api_key: str | None) -> None:
        """Guard ``app``. If ``api_key`` is ``None``, let every request through."""
        self.app = app
        self.expected = None if api_key is None else f"Bearer {api_key}".encode()

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        """Answer 401 for a wrong token. Otherwise pass the request on."""
        if self.expected is None or scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        if not secrets.compare_digest(_authorization_header(scope=scope), self.expected):
            await _unauthorized()(scope, receive, send)
            return
        await self.app(scope, receive, send)


class RequestSizeLimit:
    """Rejects a body that is larger than the limit that the server reports.

    The middleware reads ``Content-Length`` first. It rejects a request that declares a
    body over the limit. That check alone is not enough, because an HTTP/1.1 client can
    omit the header and send the body in chunks. The middleware therefore counts the body
    as it arrives. starlette writes every multipart part over 1 MiB to disk.
    """

    def __init__(self, app: ASGIApp, *, max_request_bytes: int) -> None:
        """Guard ``app``. Reject a body over ``max_request_bytes``."""
        self.app = app
        self.max_request_bytes = max_request_bytes

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        """Check the declared length, then pass the request on and count the body."""
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        declared = _content_length(scope=scope)
        if declared is not None and declared > self.max_request_bytes:
            await _too_large(max_request_bytes=self.max_request_bytes)(scope, receive, send)
            return
        await self.app(scope, self._counted(receive=receive), send)

    def _counted(self, *, receive: Receive) -> Receive:
        """Wrap ``receive`` so that the middleware measures the body as the server reads it."""
        received = 0

        async def receive_counted() -> Message:
            nonlocal received
            message = await receive()
            if message["type"] == "http.request":
                received += len(message.get("body", b""))
                if received > self.max_request_bytes:
                    # The route raises this through to the handler that FastAPI has for it.
                    raise HTTPException(
                        status_code=protocol.STATUS_PAYLOAD_TOO_LARGE,
                        detail=_too_large_detail(max_request_bytes=self.max_request_bytes),
                    )
            return message

        return receive_counted


def _authorization_header(*, scope: Scope) -> bytes:
    """Read the raw ``Authorization`` header. ASGI gives the names in lower case."""
    for name, value in scope["headers"]:
        if name == b"authorization":
            return bytes(value)
    return b""


def _content_length(*, scope: Scope) -> int | None:
    """Read the declared body length, or ``None`` if the header is absent or invalid."""
    for name, value in scope["headers"]:
        if name == b"content-length":
            try:
                return int(value)
            except ValueError:
                return None
    return None


def _too_large_detail(*, max_request_bytes: int) -> str:
    return f"The request body is over the advertised max_request_bytes of {max_request_bytes}."


def _too_large(*, max_request_bytes: int) -> JSONResponse:
    return JSONResponse(
        status_code=protocol.STATUS_PAYLOAD_TOO_LARGE,
        content={"detail": _too_large_detail(max_request_bytes=max_request_bytes)},
    )


def _unauthorized() -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_401_UNAUTHORIZED,
        content={"detail": "Missing or invalid bearer token."},
        headers={"WWW-Authenticate": "Bearer"},
    )
