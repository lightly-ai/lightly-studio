"""Makes the HTTP endpoints of the protocol from an embedder.

``create_app`` reads the capability classes that the embedder implements. It mounts one
endpoint for each class, and it always mounts ``/v1/describe``. Version 1 serves the
``texts``, ``images/bytes`` and ``videos/bytes`` transports.
"""

from __future__ import annotations

from collections.abc import Awaitable
from dataclasses import dataclass
from typing import Annotated, Any, Callable

from fastapi import APIRouter, FastAPI, File, HTTPException, Request, UploadFile, status
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, Response

from lightly_studio_serve import protocol, validation
from lightly_studio_serve.embedder import (
    Capability,
    Embedder,
    ImageBytesEmbedder,
    TextEmbedder,
    VideoBytesEmbedder,
)
from lightly_studio_serve.errors import EmbedderContractError
from lightly_studio_serve.protocol import (
    DescribeResponse,
    EmbeddingsResponse,
    EmbedTextsRequest,
    ServerLimits,
)
from lightly_studio_serve.types import EmbeddingResult

# Seconds that a client waits before it sends the request to a loading model again.
_RETRY_AFTER_SECONDS = "5"

_MultipartFiles = Annotated[list[UploadFile], File(alias=protocol.FILES_FIELD_NAME)]

_SERVED_CAPABILITIES = (
    (TextEmbedder, Capability.TEXT),
    (ImageBytesEmbedder, Capability.IMAGE_BYTES),
    (VideoBytesEmbedder, Capability.VIDEO_BYTES),
)

# The keys of a pydantic error that repeat the request body.
_ECHOED_REQUEST_KEYS = frozenset({"input", "ctx"})


@dataclass(frozen=True)
class _Mount:
    """The parts that every embed route needs. A route then mounts with two arguments."""

    router: APIRouter
    embedder: Embedder
    limits: ServerLimits


def create_app(embedder: Embedder, limits: ServerLimits | None = None) -> FastAPI:
    """Build the application that serves an embedder.

    Use this function to mount the protocol in an application of your own. You can
    also use it to test an embedder with a test client and no open port.

    Args:
        embedder: The model to serve. Its capability classes set which endpoints
            exist. A text-only embedder has no image route and no video route. It
            must accept calls from more than one thread.
        limits: The limits to report and to apply. The default is 1024 items and
            32 MiB for each request.

    Returns:
        An application that serves ``/v1/describe`` and the capabilities of the
        embedder.

    Raises:
        ValueError: If the embedder implements no capability that version 1 serves.
    """
    resolved_limits = limits if limits is not None else ServerLimits()
    app = FastAPI(title="LightlyStudio embedding server")
    app.add_exception_handler(EmbedderContractError, _handle_contract_error)
    app.add_exception_handler(RequestValidationError, _handle_invalid_request)
    app.add_exception_handler(Exception, _handle_embedder_error)
    router = APIRouter()
    _mount_describe(router=router, embedder=embedder, limits=resolved_limits)
    embed_paths = _mount_embed_routes(router=router, embedder=embedder, limits=resolved_limits)
    if not embed_paths:
        served = [base.__name__ for base, _ in _SERVED_CAPABILITIES]
        raise ValueError(
            f"{type(embedder).__name__} implements no capability that version 1 serves, so "
            f"the server would have no embed endpoint. Implement one of {served}."
        )
    _guard_readiness(app=app, embedder=embedder, paths=embed_paths)
    app.include_router(router)
    return app


def _guard_readiness(app: FastAPI, embedder: Embedder, paths: frozenset[str]) -> None:
    """Answer 503 on an embed path while the model loads, before the body is read.

    A dependency of a route runs after FastAPI has parsed the body, so an upload to a
    loading model would first be spooled to disk. ``/v1/describe`` stays outside the guard,
    because a client polls it to learn when to retry.
    """

    @app.middleware("http")
    async def verify_readiness(
        request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        if request.url.path in paths and not embedder.ready:
            return JSONResponse(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                content={"detail": "The model is still loading."},
                headers={"Retry-After": _RETRY_AFTER_SECONDS},
            )
        return await call_next(request)


def _mount_describe(router: APIRouter, embedder: Embedder, limits: ServerLimits) -> None:
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


def _mount_embed_routes(
    router: APIRouter, embedder: Embedder, limits: ServerLimits
) -> frozenset[str]:
    """Mount one endpoint per served capability, and name the paths that it mounted."""
    mount = _Mount(router=router, embedder=embedder, limits=limits)
    paths = []
    if isinstance(embedder, TextEmbedder):
        _mount_texts(mount=mount, embed=embedder.embed_text)
        paths.append(protocol.EMBED_TEXTS_PATH)
    if isinstance(embedder, ImageBytesEmbedder):
        _mount_bytes(
            mount=mount,
            path=protocol.EMBED_IMAGES_BYTES_PATH,
            embed=embedder.embed_image_bytes,
        )
        paths.append(protocol.EMBED_IMAGES_BYTES_PATH)
    if isinstance(embedder, VideoBytesEmbedder):
        _mount_bytes(
            mount=mount,
            path=protocol.EMBED_VIDEOS_BYTES_PATH,
            embed=embedder.embed_video_bytes,
        )
        paths.append(protocol.EMBED_VIDEOS_BYTES_PATH)
    return frozenset(paths)


def _mount_texts(mount: _Mount, embed: Callable[[list[str]], EmbeddingResult]) -> None:
    @mount.router.post(protocol.EMBED_TEXTS_PATH)
    def embed_texts(request: EmbedTextsRequest) -> EmbeddingsResponse:
        _check_batch_size(item_count=len(request.texts), limits=mount.limits)
        result = embed(request.texts)
        return _respond(result=result, mount=mount, item_count=len(request.texts))


def _mount_bytes(mount: _Mount, path: str, embed: Callable[[list[bytes]], EmbeddingResult]) -> None:
    """Mount one of the two bytes endpoints. Only the path is different."""

    # A synchronous handler runs the forward pass in a worker thread, not on the loop.
    @mount.router.post(path)
    def embed_bytes(files: _MultipartFiles) -> EmbeddingsResponse:
        # The parser reads the whole body first, so the 413 arrives after the upload.
        _check_batch_size(item_count=len(files), limits=mount.limits)
        items = [_read_part(file=file) for file in files]
        result = embed(items)
        return _respond(result=result, mount=mount, item_count=len(items))


def _read_part(file: UploadFile) -> bytes:
    """Read one multipart part and release the copy that starlette wrote for it."""
    data = file.file.read()
    file.file.close()
    return data


def _capabilities(embedder: Embedder) -> list[Capability]:
    """List the capabilities that the server serves. These are the mounted endpoints."""
    return [capability for base, capability in _SERVED_CAPABILITIES if isinstance(embedder, base)]


def _respond(result: EmbeddingResult, mount: _Mount, item_count: int) -> EmbeddingsResponse:
    spec = mount.embedder.embedding_space_spec()
    return validation.build_embeddings_response(
        result=result,
        space_key=spec.space_key,
        dimension=spec.dimension,
        item_count=item_count,
    )


def _check_batch_size(item_count: int, limits: ServerLimits) -> None:
    if item_count > limits.max_batch_size:
        raise HTTPException(
            status_code=protocol.STATUS_PAYLOAD_TOO_LARGE,
            detail=f"The request carries {item_count} items, over the advertised "
            f"max_batch_size of {limits.max_batch_size}.",
        )


def _handle_contract_error(_request: Request, exc: Exception) -> Response:
    """Answer 500 and name the result of the embedder. Do not send that result."""
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, content={"detail": str(exc)}
    )


def _handle_embedder_error(_request: Request, exc: Exception) -> Response:
    """Answer 500 in the shape that every other error of this server has.

    Anything a model raises other than an ``EmbedderContractError`` would reach the
    default handler of starlette, which answers plain text. The message names the class
    alone, because the text of an exception can hold the input that it failed on.
    Starlette raises the exception again, so the traceback still reaches the log.
    """
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": f"The embedder raised {type(exc).__name__}. See the server log."},
    )


def _handle_invalid_request(_request: Request, exc: Exception) -> Response:
    """Answer 400. The protocol keeps 422 for input that the server cannot use.

    FastAPI answers 422 for both cases. The two cases need opposite actions from a
    client. A malformed request is a fault in the client. Unusable input is a fault in
    the batch.
    """
    errors = exc.errors() if isinstance(exc, RequestValidationError) else []
    detail = [_without_request_content(error=error) for error in errors]
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST, content={"detail": jsonable_encoder(detail)}
    )


def _without_request_content(error: Any) -> dict[str, Any]:
    """Keep the field and the rule of one error, and drop what repeats the request.

    ``input`` holds the value that failed, and ``ctx`` can hold it again. On a bytes
    endpoint that value is the content of a part.
    """
    return {key: value for key, value in error.items() if key not in _ECHOED_REQUEST_KEYS}
