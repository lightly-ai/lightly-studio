"""Turns an embedder into the HTTP endpoints the protocol defines.

``create_app`` inspects which capability classes the embedder implements, mounts
those endpoints plus ``/v1/describe``, and returns the application. Version 1
serves the ``texts``, ``images/bytes`` and ``videos/bytes`` transports; the URL
transports are specified but not mounted, because LightlyStudio does not call them
yet and capabilities are advertised, so adding them later is purely additive.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Annotated, Callable

from fastapi import (
    APIRouter,
    Depends,
    FastAPI,
    File,
    HTTPException,
    Request,
    UploadFile,
    status,
)
from fastapi import params as fastapi_params
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, Response

from lightly_studio_embed import protocol, validation
from lightly_studio_embed.embedder import (
    BaseEmbedder,
    ImageBytesEmbedder,
    TextEmbedder,
    VideoBytesEmbedder,
)
from lightly_studio_embed.errors import CapabilityNotImplementedError, EmbedderContractError
from lightly_studio_embed.protocol import (
    DescribeResponse,
    EmbeddingsResponse,
    EmbedTextsRequest,
    ServerLimits,
    WireCapability,
)
from lightly_studio_embed.types import EmbeddingResult

# How long a client should wait before retrying a model that is still loading.
_RETRY_AFTER_SECONDS = "5"

_MultipartFiles = Annotated[list[UploadFile], File(alias=protocol.FILES_FIELD_NAME)]


@dataclass(frozen=True)
class _Mount:
    """What every embed route is built from, so each mounts with two arguments."""

    router: APIRouter
    embedder: BaseEmbedder
    limits: ServerLimits
    guards: Sequence[fastapi_params.Depends]


def create_app(*, embedder: BaseEmbedder, limits: ServerLimits | None = None) -> FastAPI:
    """Build the application that serves an embedder.

    Use it to mount the protocol inside an application of your own, or to exercise
    an embedder over a test client without binding a port.

    Args:
        embedder: The model to serve. Its capability classes decide which endpoints
            exist: a text-only embedder exposes no image or video routes.
        limits: Ceilings to advertise and enforce. Defaults to 64 items and 32 MiB
            per request.

    Returns:
        An application serving ``/v1/describe`` and the embedder's capabilities.
    """
    resolved_limits = limits if limits is not None else ServerLimits()
    app = FastAPI(title="LightlyStudio embedding server")
    app.add_exception_handler(EmbedderContractError, _handle_contract_error)
    app.add_exception_handler(RequestValidationError, _handle_invalid_request)
    router = APIRouter()
    _mount_describe(router=router, embedder=embedder, limits=resolved_limits)
    _mount_embed_routes(router=router, embedder=embedder, limits=resolved_limits)
    app.include_router(router)
    return app


def _mount_describe(*, router: APIRouter, embedder: BaseEmbedder, limits: ServerLimits) -> None:
    @router.get(protocol.DESCRIBE_PATH)
    def describe() -> DescribeResponse:
        spec = embedder.embedding_space_spec()
        return DescribeResponse(
            protocol_version=protocol.PROTOCOL_VERSION,
            space_key=spec.space_key,
            dimension=spec.dimension,
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
    spec = mount.embedder.embedding_space_spec()
    return validation.build_embeddings_response(
        result=result,
        space_key=spec.space_key,
        dimension=spec.dimension,
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
