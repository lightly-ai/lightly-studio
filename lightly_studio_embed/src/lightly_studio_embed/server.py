"""Makes the HTTP endpoints of the protocol from an embedder.

``create_app`` reads the capability classes that the embedder implements. It mounts one
endpoint for each class, and it always mounts ``/v1/describe``. Version 1 serves the
``texts``, ``images/bytes`` and ``videos/bytes`` transports.
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
    Capability,
    Embedder,
    ImageBytesEmbedder,
    TextEmbedder,
    VideoBytesEmbedder,
)
from lightly_studio_embed.errors import EmbedderContractError
from lightly_studio_embed.protocol import (
    DescribeResponse,
    EmbeddingsResponse,
    EmbedTextsRequest,
    ServerLimits,
)
from lightly_studio_embed.types import EmbeddingResult

# Seconds that a client waits before it sends the request to a loading model again.
_RETRY_AFTER_SECONDS = "5"

_MultipartFiles = Annotated[list[UploadFile], File(alias=protocol.FILES_FIELD_NAME)]


@dataclass(frozen=True)
class _Mount:
    """The parts that every embed route needs. A route then mounts with two arguments."""

    router: APIRouter
    embedder: Embedder
    limits: ServerLimits
    guards: Sequence[fastapi_params.Depends]


def create_app(*, embedder: Embedder, limits: ServerLimits | None = None) -> FastAPI:
    """Build the application that serves an embedder.

    Use this function to mount the protocol in an application of your own. You can
    also use it to test an embedder with a test client and no open port.

    Args:
        embedder: The model to serve. Its capability classes set which endpoints
            exist. A text-only embedder has no image route and no video route.
        limits: The limits to report and to apply. The default is 1024 items and
            32 MiB for each request.

    Returns:
        An application that serves ``/v1/describe`` and the capabilities of the
        embedder.
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


def _mount_describe(*, router: APIRouter, embedder: Embedder, limits: ServerLimits) -> None:
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


def _mount_embed_routes(*, router: APIRouter, embedder: Embedder, limits: ServerLimits) -> None:
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
        result = embed(request.texts)
        return _respond(result=result, mount=mount, item_count=len(request.texts))


def _mount_bytes(
    *, mount: _Mount, path: str, embed: Callable[[list[bytes]], EmbeddingResult]
) -> None:
    """Mount one of the two bytes endpoints. Only the path is different."""

    # A synchronous handler runs the forward pass in a worker thread, not on the loop.
    @mount.router.post(path, dependencies=mount.guards)
    def embed_bytes(files: _MultipartFiles) -> EmbeddingsResponse:
        _check_batch_size(item_count=len(files), limits=mount.limits)
        items = [_read_part(file=file) for file in files]
        result = embed(items)
        return _respond(result=result, mount=mount, item_count=len(items))


def _read_part(*, file: UploadFile) -> bytes:
    """Read one multipart part and release the copy that starlette wrote for it."""
    data = file.file.read()
    file.file.close()
    return data


def _capabilities(*, embedder: Embedder) -> list[Capability]:
    """List the capabilities that the server serves. These are the mounted endpoints."""
    served = [
        (TextEmbedder, Capability.TEXT),
        (ImageBytesEmbedder, Capability.IMAGE_BYTES),
        (VideoBytesEmbedder, Capability.VIDEO_BYTES),
    ]
    return [capability for base, capability in served if isinstance(embedder, base)]


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


def _readiness(*, embedder: Embedder) -> Callable[[], None]:
    def verify() -> None:
        if not embedder.ready:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="The model is still loading.",
                headers={"Retry-After": _RETRY_AFTER_SECONDS},
            )

    return verify


def _handle_contract_error(_request: Request, exc: Exception) -> Response:
    """Answer 500 and name the result of the embedder. Do not send that result."""
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, content={"detail": str(exc)}
    )


def _handle_invalid_request(_request: Request, exc: Exception) -> Response:
    """Answer 400. The protocol keeps 422 for input that the server cannot use.

    FastAPI answers 422 for both cases. The two cases need opposite actions from a
    client. A malformed request is a fault in the client. Unusable input is a fault in
    the batch.
    """
    errors = exc.errors() if isinstance(exc, RequestValidationError) else []
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST, content={"detail": jsonable_encoder(errors)}
    )
