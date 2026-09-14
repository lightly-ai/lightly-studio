"""ASGI middleware that checks a request before FastAPI reads its body.

None of these checks can be a dependency. FastAPI reads the full body before it solves
the dependencies. A dependency therefore runs after an unknown peer sets how much memory
the server holds, and after a multipart upload to a loading model is spooled to disk.
"""

from __future__ import annotations

import secrets
from collections.abc import Collection

from fastapi import HTTPException, status
from fastapi.responses import JSONResponse
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from lightly_studio_serve import protocol
from lightly_studio_serve.embedder import Embedder

# Seconds that a client waits before it sends the request to a loading model again.
_RETRY_AFTER_SECONDS = "5"

# RFC 7235 makes the scheme case-insensitive, so the check lowers the one it reads.
_BEARER_SCHEME = b"bearer"


class BearerAuth:
    """Rejects a request with a missing or wrong bearer token.

    The class compares the raw bytes that the client sent. It does not decode the header
    first. One byte that is not ASCII raises an error inside ``secrets.compare_digest``,
    and the server then answers 500. The protocol needs 401.
    """

    def __init__(self, app: ASGIApp, api_key: str | None, open_paths: Collection[str] = ()) -> None:
        """Guard ``app``. If ``api_key`` is ``None``, let every request through.

        Args:
            app: The application to guard.
            api_key: The token that a client must send, or ``None`` to guard nothing.
            open_paths: The paths that need no token. The interactive documentation
                goes here: a browser puts no header on it, and it holds only the
                protocol, which is public.
        """
        self.app = app
        self.expected = None if api_key is None else api_key.encode()
        self.open_paths = frozenset(open_paths)

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        """Answer 401 for a wrong token. Otherwise pass the request on."""
        expected = self.expected
        if expected is None or scope["type"] != "http" or scope["path"] in self.open_paths:
            await self.app(scope, receive, send)
            return
        if not _has_valid_token(scope=scope, expected=expected):
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

    def __init__(self, app: ASGIApp, max_request_bytes: int) -> None:
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

    def _counted(self, receive: Receive) -> Receive:
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


class Readiness:
    """Rejects a request to an embed path while the model is still loading.

    ``/v1/describe`` is not among the paths. A client polls it to learn when to retry.
    """

    def __init__(self, app: ASGIApp, embedder: Embedder, paths: Collection[str]) -> None:
        """Guard ``paths`` while ``embedder`` reports that it is not ready."""
        self.app = app
        self.embedder = embedder
        self.paths = frozenset(paths)

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        """Answer 503 while the model loads. Otherwise pass the request on."""
        if scope["type"] != "http" or scope["path"] not in self.paths or self.embedder.ready:
            await self.app(scope, receive, send)
            return
        await _unavailable()(scope, receive, send)


def _has_valid_token(scope: Scope, expected: bytes) -> bool:
    """Whether the request carries ``expected`` as its bearer token."""
    token = _bearer_token(scope=scope)
    if not token:
        return False
    return secrets.compare_digest(token, expected)


def _bearer_token(scope: Scope) -> bytes:
    """Read the token out of the ``Authorization`` header, or ``b""`` if there is none.

    RFC 7235 writes the credentials as a scheme, then space, then the token. The scheme
    is case-insensitive and more than one space is legal, so a client that follows the
    standard must not meet a 401.
    """
    scheme, _, token = _authorization_header(scope=scope).partition(b" ")
    if scheme.lower() != _BEARER_SCHEME:
        return b""
    return token.strip()


def _authorization_header(scope: Scope) -> bytes:
    """Read the raw ``Authorization`` header. ASGI gives the names in lower case."""
    for name, value in scope["headers"]:
        if name == b"authorization":
            return bytes(value)
    return b""


def _content_length(scope: Scope) -> int | None:
    """Read the declared body length, or ``None`` if the header is absent or invalid."""
    for name, value in scope["headers"]:
        if name == b"content-length":
            try:
                return int(value)
            except ValueError:
                return None
    return None


def _too_large_detail(max_request_bytes: int) -> str:
    return f"The request body is over the advertised max_request_bytes of {max_request_bytes}."


def _too_large(max_request_bytes: int) -> JSONResponse:
    return JSONResponse(
        status_code=protocol.STATUS_PAYLOAD_TOO_LARGE,
        content={"detail": _too_large_detail(max_request_bytes=max_request_bytes)},
    )


def _unavailable() -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        content={"detail": "The model is still loading."},
        headers={"Retry-After": _RETRY_AFTER_SECONDS},
    )


def _unauthorized() -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_401_UNAUTHORIZED,
        content={"detail": "Missing or invalid bearer token."},
        headers={"WWW-Authenticate": "Bearer"},
    )
