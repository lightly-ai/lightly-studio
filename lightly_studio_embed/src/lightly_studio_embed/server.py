"""Turns an embedder into the HTTP endpoints the protocol defines.

``serve`` inspects which capability classes the embedder implements, mounts those
endpoints plus ``/v1/describe``, and runs uvicorn. Version 1 serves the ``texts``,
``images/bytes`` and ``videos/bytes`` transports; the URL transports are specified
but not mounted, because LightlyStudio does not call them yet and capabilities are
advertised, so adding them later is purely additive.

The bearer token and the request size ceiling are enforced in the ASGI middleware
of ``lightly_studio_embed.middleware``, which runs ahead of routing.
"""

from __future__ import annotations

import warnings
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Annotated, Callable

import uvicorn
from fastapi import APIRouter, Depends, FastAPI, File, HTTPException, Request, UploadFile, status
from fastapi import params as fastapi_params
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, Response

from lightly_studio_embed import protocol, validation
from lightly_studio_embed.embedder import (
    BaseEmbedder,
    EmbeddingResult,
    ImageBytesEmbedder,
    TextEmbedder,
    VideoBytesEmbedder,
)
from lightly_studio_embed.errors import CapabilityNotImplementedError, EmbedderContractError
from lightly_studio_embed.middleware import BearerAuth, RequestSizeLimit
from lightly_studio_embed.protocol import (
    DescribeResponse,
    EmbeddingsResponse,
    EmbedTextsRequest,
    ServerLimits,
    WireCapability,
)

# How long a client should wait before retrying a model that is still loading.
_RETRY_AFTER_SECONDS = "5"

# Binding to one of these keeps the port unreachable from other hosts.
_LOOPBACK_HOSTS = frozenset({"127.0.0.1", "::1", "localhost"})

_MultipartFiles = Annotated[list[UploadFile], File(alias=protocol.FILES_FIELD_NAME)]


@dataclass(frozen=True)
class _Mount:
    """What every embed route is built from, so each mounts with two arguments."""

    router: APIRouter
    embedder: BaseEmbedder
    limits: ServerLimits
    guards: Sequence[fastapi_params.Depends]


# PLR0913: `serve` is the one function a customer calls, and every argument is a knob they set
# on their own. Folding them into a config object would only move the list somewhere else.
def serve(  # noqa: PLR0913
    embedder: BaseEmbedder,
    *,
    host: str = "127.0.0.1",
    port: int = 8080,
    api_key: str | None = None,
    limits: ServerLimits | None = None,
    ssl_certfile: str | Path | None = None,
    ssl_keyfile: str | Path | None = None,
) -> None:
    """Serve an embedder over HTTP until the process is stopped.

    Args:
        embedder: The model to serve. Its capability classes decide which endpoints
            exist: a text-only embedder exposes no image or video routes.
        host: Interface to bind. The default is loopback only; pass ``"0.0.0.0"`` to
            accept requests from other hosts.
        port: TCP port to bind.
        api_key: Token a client must send as ``Authorization: Bearer <api_key>``.
            ``None`` leaves the server unauthenticated, which is only safe behind a
            loopback bind or a trusted network boundary.
        limits: Ceilings to advertise and enforce. Defaults to 64 items and 32 MiB
            per request.
        ssl_certfile: PEM certificate chain to serve HTTPS with. Give it, or
            terminate TLS in a proxy in front, for any bind other than loopback: the
            bearer token travels in the request otherwise, in the clear. ``serve``
            warns when neither is in place.
        ssl_keyfile: Private key for ``ssl_certfile``, unless the certificate file
            already carries it.

    Raises:
        ValueError: If ``api_key`` is given but blank, or if ``ssl_keyfile`` is given
            without ``ssl_certfile``.
    """
    if ssl_keyfile is not None and ssl_certfile is None:
        raise ValueError("ssl_keyfile was given without ssl_certfile, so TLS cannot start.")
    if host not in _LOOPBACK_HOSTS:
        exposure = _public_bind_warning(
            host=host, api_key=api_key, has_tls=ssl_certfile is not None
        )
        if exposure is not None:
            warnings.warn(exposure, stacklevel=2)
    app = create_app(embedder=embedder, api_key=api_key, limits=limits)
    uvicorn.run(app, host=host, port=port, ssl_certfile=ssl_certfile, ssl_keyfile=ssl_keyfile)


def _public_bind_warning(*, host: str, api_key: str | None, has_tls: bool) -> str | None:
    """Name what a bind reachable from other hosts exposes, or ``None`` if it is covered."""
    if api_key is None:
        return (
            f"Serving on {host} without an api_key: everyone who can reach the port can use "
            "the model. Pass api_key, or bind a loopback address."
        )
    if not has_tls:
        return (
            f"Serving on {host} over plain HTTP: the bearer token travels in the clear. Pass "
            "ssl_certfile, terminate TLS in a proxy in front, or bind a loopback address."
        )
    return None


def create_app(
    *,
    embedder: BaseEmbedder,
    api_key: str | None = None,
    limits: ServerLimits | None = None,
) -> FastAPI:
    """Build the application ``serve`` runs.

    Use it to mount the protocol inside an application of your own, or to exercise
    an embedder over a test client without binding a port.

    Args:
        embedder: The model to serve.
        api_key: Token a client must send as ``Authorization: Bearer <api_key>``.
        limits: Ceilings to advertise and enforce.

    Returns:
        An application serving ``/v1/describe`` and the embedder's capabilities.

    Raises:
        ValueError: If ``api_key`` is given but blank, which would otherwise leave a
            server that looks authenticated while accepting an empty token.
    """
    if api_key is not None and not api_key.strip():
        raise ValueError("api_key is blank. Pass a token, or None to serve unauthenticated.")
    resolved_limits = limits if limits is not None else ServerLimits()
    app = FastAPI(title="LightlyStudio embedding server")
    app.add_exception_handler(EmbedderContractError, _handle_contract_error)
    app.add_exception_handler(RequestValidationError, _handle_invalid_request)
    # Added innermost first, so the token is checked before a body is even counted.
    app.add_middleware(RequestSizeLimit, max_request_bytes=resolved_limits.max_request_bytes)
    app.add_middleware(BearerAuth, api_key=api_key)
    router = APIRouter()
    _mount_describe(router=router, embedder=embedder, limits=resolved_limits)
    _mount_embed_routes(router=router, embedder=embedder, limits=resolved_limits)
    app.include_router(router)
    return app


def _mount_describe(*, router: APIRouter, embedder: BaseEmbedder, limits: ServerLimits) -> None:
    @router.get(protocol.DESCRIBE_PATH)
    def describe() -> DescribeResponse:
        return DescribeResponse(
            protocol_version=protocol.PROTOCOL_VERSION,
            space_key=embedder.space_key,
            dimension=embedder.dimension,
            ready=embedder.ready,
            capabilities=_capabilities(embedder=embedder),
            limits=limits,
        )


def _mount_embed_routes(*, router: APIRouter, embedder: BaseEmbedder, limits: ServerLimits) -> None:
    mount = _Mount(
        router=router,
        embedder=embedder,
        limits=limits,
        guards=[Depends(_readiness(embedder=embedder))],
    )
    if isinstance(embedder, TextEmbedder):
        _mount_texts(mount=mount, embed=embedder.embed_text)
    if isinstance(embedder, ImageBytesEmbedder):
        _mount_bytes(
            mount=mount,
            path=protocol.EMBED_IMAGES_BYTES_PATH,
            embed=embedder.embed_image_bytes,
        )
    if isinstance(embedder, VideoBytesEmbedder):
        _mount_bytes(
            mount=mount,
            path=protocol.EMBED_VIDEOS_BYTES_PATH,
            embed=embedder.embed_video_bytes,
        )


def _mount_texts(*, mount: _Mount, embed: Callable[[list[str]], EmbeddingResult]) -> None:
    @mount.router.post(protocol.EMBED_TEXTS_PATH, dependencies=mount.guards)
    def embed_texts(request: EmbedTextsRequest) -> EmbeddingsResponse:
        _check_batch_size(item_count=len(request.texts), limits=mount.limits)
        result = _embed(lambda: embed(request.texts))
        return _respond(result=result, mount=mount, item_count=len(request.texts))


def _mount_bytes(
    *, mount: _Mount, path: str, embed: Callable[[list[bytes]], EmbeddingResult]
) -> None:
    """Mount one of the two bytes endpoints; they differ only in the path."""

    # A synchronous handler, so that FastAPI runs the forward pass in a worker
    # thread rather than on the event loop.
    @mount.router.post(path, dependencies=mount.guards)
    def embed_bytes(files: _MultipartFiles) -> EmbeddingsResponse:
        _check_batch_size(item_count=len(files), limits=mount.limits)
        items = [_read_part(file=file) for file in files]
        result = _embed(lambda: embed(items))
        return _respond(result=result, mount=mount, item_count=len(items))


def _read_part(*, file: UploadFile) -> bytes:
    """Read one multipart part, releasing the copy starlette spooled for it."""
    data = file.file.read()
    file.file.close()
    return data


def _capabilities(*, embedder: BaseEmbedder) -> list[WireCapability]:
    served = [
        (TextEmbedder, WireCapability.TEXT),
        (ImageBytesEmbedder, WireCapability.IMAGE_BYTES),
        (VideoBytesEmbedder, WireCapability.VIDEO_BYTES),
    ]
    return [capability for base, capability in served if isinstance(embedder, base)]


def _embed(call: Callable[[], EmbeddingResult]) -> EmbeddingResult:
    """Run an embedder call, mapping a capability left unfinished to 501."""
    try:
        return call()
    except CapabilityNotImplementedError as error:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="The server mounts this capability but does not implement it.",
        ) from error


def _respond(*, result: EmbeddingResult, mount: _Mount, item_count: int) -> EmbeddingsResponse:
    return validation.build_embeddings_response(
        result=result,
        space_key=mount.embedder.space_key,
        dimension=mount.embedder.dimension,
        item_count=item_count,
    )


def _check_batch_size(*, item_count: int, limits: ServerLimits) -> None:
    if item_count > limits.max_batch_size:
        raise HTTPException(
            status_code=protocol.STATUS_PAYLOAD_TOO_LARGE,
            detail=f"The request carries {item_count} items, over the advertised "
            f"max_batch_size of {limits.max_batch_size}.",
        )


def _readiness(*, embedder: BaseEmbedder) -> Callable[[], None]:
    def verify() -> None:
        if not embedder.ready:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="The model is still loading.",
                headers={"Retry-After": _RETRY_AFTER_SECONDS},
            )

    return verify


def _handle_contract_error(_request: Request, exc: Exception) -> Response:
    """Answer 500 naming what the embedder returned, rather than shipping it."""
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, content={"detail": str(exc)}
    )


def _handle_invalid_request(_request: Request, exc: Exception) -> Response:
    """Answer 400, because the protocol reserves 422 for input it cannot use.

    FastAPI answers 422 for both by default, and the two carry opposite advice for a
    client: a malformed request is its own bug, unusable input is the batch's.
    """
    errors = exc.errors() if isinstance(exc, RequestValidationError) else []
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST, content={"detail": jsonable_encoder(errors)}
    )
