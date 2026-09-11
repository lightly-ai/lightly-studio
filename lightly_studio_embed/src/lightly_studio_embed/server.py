"""Makes the HTTP endpoints of the protocol from an embedder.

``create_app`` reads the capability classes that the embedder implements. It mounts one
endpoint for each class, and it always mounts ``/v1/describe``. ``serve`` runs that
application with uvicorn. Version 1 serves the ``texts``, ``images/bytes`` and
``videos/bytes`` transports.

The ASGI middleware in ``lightly_studio_embed.middleware`` applies the bearer token and
the request size limit. That middleware runs before the router.
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
    Capability,
    Embedder,
    ImageBytesEmbedder,
    TextEmbedder,
    VideoBytesEmbedder,
)
from lightly_studio_embed.errors import EmbedderContractError
from lightly_studio_embed.middleware import BearerAuth, RequestSizeLimit
from lightly_studio_embed.protocol import (
    DescribeResponse,
    EmbeddingsResponse,
    EmbedTextsRequest,
    ServerLimits,
)
from lightly_studio_embed.types import EmbeddingResult

# Seconds that a client waits before it sends the request to a loading model again.
_RETRY_AFTER_SECONDS = "5"

# A port on one of these addresses is not reachable from other hosts.
_LOOPBACK_HOSTS = frozenset({"127.0.0.1", "::1", "localhost"})

_MultipartFiles = Annotated[list[UploadFile], File(alias=protocol.FILES_FIELD_NAME)]


@dataclass(frozen=True)
class _Mount:
    """The parts that every embed route needs. A route then mounts with two arguments."""

    router: APIRouter
    embedder: Embedder
    limits: ServerLimits
    guards: Sequence[fastapi_params.Depends]


# PLR0913: A customer sets each argument of `serve`. A config object moves the same list.
def serve(  # noqa: PLR0913
    embedder: Embedder,
    *,
    host: str = "127.0.0.1",
    port: int = 8080,
    api_key: str | None = None,
    limits: ServerLimits | None = None,
    ssl_certfile: str | Path | None = None,
    ssl_keyfile: str | Path | None = None,
) -> None:
    """Serve an embedder over HTTP until the process stops.

    Args:
        embedder: The model to serve. Its capability classes set which endpoints
            exist. A text-only embedder has no image route and no video route.
        host: The interface to bind. The default binds loopback only. Give
            ``"0.0.0.0"`` to accept requests from other hosts.
        port: The TCP port to bind.
        api_key: The token that a client must send as
            ``Authorization: Bearer <api_key>``. ``None`` leaves the server open.
            That is safe only on a loopback address or inside a network that you
            trust.
        limits: The limits to report and to apply. The default is 1024 items and
            32 MiB for each request.
        ssl_certfile: The PEM certificate chain for HTTPS. Give this file for any
            address that is not loopback. You can also end TLS at a proxy in front of
            the server. Without one of these, the bearer token crosses the network in
            clear text. ``serve`` gives a warning when it has no certificate.
        ssl_keyfile: The private key for ``ssl_certfile``. Omit it if the
            certificate file already holds the key.

    Raises:
        ValueError: If ``api_key`` is an empty or blank string, or if you give
            ``ssl_keyfile`` without ``ssl_certfile``.
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
    """Name the risk of an address that other hosts can reach, or ``None`` if there is none."""
    if api_key is None:
        return (
            f"Serving on {host} without an api_key. Every host that can reach the port can "
            "use the model. Give api_key, or bind a loopback address."
        )
    if not has_tls:
        return (
            f"Serving on {host} over plain HTTP. The bearer token goes over the network in "
            "clear text. Give ssl_certfile, or end TLS at a proxy in front of the server, or "
            "bind a loopback address."
        )
    return None


def create_app(
    *,
    embedder: Embedder,
    api_key: str | None = None,
    limits: ServerLimits | None = None,
) -> FastAPI:
    """Build the application ``serve`` runs.

    Use this function to mount the protocol in an application of your own. You can
    also use it to test an embedder with a test client and no open port.

    Args:
        embedder: The model to serve. Its capability classes set which endpoints
            exist. A text-only embedder has no image route and no video route.
        api_key: The token that a client must send as
            ``Authorization: Bearer <api_key>``.
        limits: The limits to report and to apply. The default is 1024 items and
            32 MiB for each request.

    Returns:
        An application that serves ``/v1/describe`` and the capabilities of the
        embedder.

    Raises:
        ValueError: If ``api_key`` is an empty or blank string. Such a server looks
            authenticated, but it accepts an empty token.
    """
    if api_key is not None and not api_key.strip():
        raise ValueError("api_key is blank. Pass a token, or None to serve unauthenticated.")
    resolved_limits = limits if limits is not None else ServerLimits()
    app = FastAPI(title="LightlyStudio embedding server")
    app.add_exception_handler(EmbedderContractError, _handle_contract_error)
    app.add_exception_handler(RequestValidationError, _handle_invalid_request)
    # Innermost first, so the server checks the token before it counts a body.
    app.add_middleware(RequestSizeLimit, max_request_bytes=resolved_limits.max_request_bytes)
    app.add_middleware(BearerAuth, api_key=api_key)
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
