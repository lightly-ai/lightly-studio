"""Turns an embedder into the HTTP endpoints the protocol defines.

``serve`` inspects which capability classes the embedder implements, mounts those
endpoints plus ``/v1/describe``, and runs uvicorn. Version 1 serves the ``texts``,
``images/bytes`` and ``videos/bytes`` transports; the URL transports are specified
but not mounted, because LightlyStudio does not call them yet and capabilities are
advertised, so adding them later is purely additive.
"""

from __future__ import annotations

import secrets
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Annotated, Callable

import uvicorn
from fastapi import (
    APIRouter,
    Depends,
    FastAPI,
    File,
    HTTPException,
    Request,
    Response,
    UploadFile,
    status,
)
from fastapi import params as fastapi_params
from fastapi.responses import JSONResponse

from lightly_studio_embed import protocol, validation
from lightly_studio_embed.embedder import (
    BaseEmbedder,
    EmbeddingResult,
    ImageBytesEmbedder,
    TextEmbedder,
    VideoBytesEmbedder,
)
from lightly_studio_embed.protocol import (
    DescribeResponse,
    EmbeddingsResponse,
    EmbedTextsRequest,
    ServerLimits,
    WireCapability,
)
from lightly_studio_embed.validation import EmbedderContractError

# How long a client should wait before retrying a model that is still loading.
_RETRY_AFTER_SECONDS = "5"

# Spelled out, because starlette renamed its constant for this status and the old name warns
# on new versions while the new one is missing on the versions `requires-python` still allows.
_STATUS_PAYLOAD_TOO_LARGE = 413

_MultipartFiles = Annotated[list[UploadFile], File(alias=protocol.FILES_FIELD_NAME)]


@dataclass(frozen=True)
class _Mount:
    """What every embed route is built from, so each mounts with two arguments."""

    router: APIRouter
    embedder: BaseEmbedder
    limits: ServerLimits
    guards: Sequence[fastapi_params.Depends]


def serve(
    embedder: BaseEmbedder,
    *,
    host: str = "127.0.0.1",
    port: int = 8080,
    api_key: str | None = None,
    limits: ServerLimits | None = None,
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
    """
    app = create_app(embedder=embedder, api_key=api_key, limits=limits)
    uvicorn.run(app, host=host, port=port)


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
    """
    app = FastAPI(title="LightlyStudio embedding server")
    app.add_exception_handler(EmbedderContractError, _handle_contract_error)
    resolved_limits = limits if limits is not None else ServerLimits()
    router = APIRouter(
        prefix=protocol.BASE_PATH, dependencies=[Depends(_authorization(api_key=api_key))]
    )
    _mount_describe(router=router, embedder=embedder, limits=resolved_limits)
    _mount_embed_routes(router=router, embedder=embedder, limits=resolved_limits)
    app.include_router(router)
    return app


def _mount_describe(*, router: APIRouter, embedder: BaseEmbedder, limits: ServerLimits) -> None:
    @router.get("/describe")
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
        guards=[Depends(_readiness(embedder=embedder)), Depends(_request_size(limits=limits))],
    )
    if isinstance(embedder, TextEmbedder):
        _mount_texts(mount=mount, embed=embedder.embed_text)
    if isinstance(embedder, ImageBytesEmbedder):
        _mount_bytes(mount=mount, path="/embed/images/bytes", embed=embedder.embed_image_bytes)
    if isinstance(embedder, VideoBytesEmbedder):
        _mount_bytes(mount=mount, path="/embed/videos/bytes", embed=embedder.embed_video_bytes)


def _mount_texts(*, mount: _Mount, embed: Callable[[list[str]], EmbeddingResult]) -> None:
    @mount.router.post("/embed/texts", dependencies=mount.guards)
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
        items = [file.file.read() for file in files]
        result = _embed(lambda: embed(items))
        return _respond(result=result, mount=mount, item_count=len(items))


def _capabilities(*, embedder: BaseEmbedder) -> list[WireCapability]:
    served = [
        (TextEmbedder, WireCapability.TEXT),
        (ImageBytesEmbedder, WireCapability.IMAGE_BYTES),
        (VideoBytesEmbedder, WireCapability.VIDEO_BYTES),
    ]
    return [capability for base, capability in served if isinstance(embedder, base)]


def _embed(call: Callable[[], EmbeddingResult]) -> EmbeddingResult:
    """Run an embedder call, mapping a method left unimplemented to 501."""
    try:
        return call()
    except NotImplementedError as error:
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
            status_code=_STATUS_PAYLOAD_TOO_LARGE,
            detail=f"The request carries {item_count} items, over the advertised "
            f"max_batch_size of {limits.max_batch_size}.",
        )


def _authorization(*, api_key: str | None) -> Callable[[Request], None]:
    def verify(request: Request) -> None:
        if api_key is None:
            return
        header = request.headers.get("authorization", "")
        if not secrets.compare_digest(header, f"Bearer {api_key}"):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Missing or invalid bearer token.",
                headers={"WWW-Authenticate": "Bearer"},
            )

    return verify


def _readiness(*, embedder: BaseEmbedder) -> Callable[[], None]:
    def verify() -> None:
        if not embedder.ready:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="The model is still loading.",
                headers={"Retry-After": _RETRY_AFTER_SECONDS},
            )

    return verify


def _request_size(*, limits: ServerLimits) -> Callable[[Request], None]:
    def verify(request: Request) -> None:
        content_length = request.headers.get("content-length", "")
        if content_length.isdigit() and int(content_length) > limits.max_request_bytes:
            raise HTTPException(
                status_code=_STATUS_PAYLOAD_TOO_LARGE,
                detail=f"The request body is over the advertised max_request_bytes of "
                f"{limits.max_request_bytes}.",
            )

    return verify


def _handle_contract_error(_request: Request, exc: Exception) -> Response:
    """Answer 500 naming what the embedder returned, rather than shipping it."""
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, content={"detail": str(exc)}
    )
