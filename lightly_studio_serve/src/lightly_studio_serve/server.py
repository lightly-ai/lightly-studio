"""Makes the HTTP endpoints of the protocol from an embedder.

``create_app`` reads the capability classes that the embedder implements. It mounts one
endpoint for each class, and it always mounts ``/v1/describe``. ``serve`` runs that
application with uvicorn. Version 1 serves the ``texts``, ``images/bytes`` and
``videos/bytes`` transports.

The ASGI middleware in ``lightly_studio_serve.middleware`` applies the bearer token, the
readiness of the model and the request size limit. That middleware runs before the router.
"""

from __future__ import annotations

import ipaddress
import warnings
from dataclasses import dataclass
from pathlib import Path
from typing import Annotated, Any, Callable

import uvicorn
from fastapi import APIRouter, Depends, FastAPI, File, HTTPException, Request, UploadFile, status
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, Response
from fastapi.security import HTTPBearer

from lightly_studio_serve import protocol, validation
from lightly_studio_serve.embedder import (
    Capability,
    Embedder,
    ImageBytesEmbedder,
    TextEmbedder,
    VideoBytesEmbedder,
)
from lightly_studio_serve.errors import EmbedderContractError
from lightly_studio_serve.middleware import BearerAuth, Readiness, RequestSizeLimit
from lightly_studio_serve.protocol import (
    DescribeResponse,
    EmbeddingsResponse,
    EmbedTextsRequest,
    ServerLimits,
)
from lightly_studio_serve.types import EmbeddingResult

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


# PLR0913: A customer sets each argument of `serve`. A config object moves the same list.
def serve(  # noqa: PLR0913
    embedder: Embedder,
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
            exist. A text-only embedder has no image route and no video route. It
            must accept calls from more than one thread.
        host: The interface to bind. The default binds loopback only. Give
            ``"0.0.0.0"`` to accept requests from other hosts.
        port: The TCP port to bind.
        api_key: The token that a client must send as
            ``Authorization: Bearer <api_key>``. ``None`` leaves the server open.
            That is safe only on a loopback address or inside a network that you
            trust. The server trims the whitespace around the token, because a
            client cannot send it, and it gives a warning when it does.
        limits: The limits to report and to apply. The default is 999 items and
            32 MiB for each request.
        ssl_certfile: The PEM certificate chain for HTTPS. Give this file for any
            address that is not loopback. You can also end TLS at a proxy in front of
            the server. Without one of these, the bearer token crosses the network in
            clear text. ``serve`` gives a warning when it has no certificate.
        ssl_keyfile: The private key for ``ssl_certfile``. Omit it if the
            certificate file already holds the key.

    Raises:
        ValueError: If ``api_key`` is an empty or blank string, if you give
            ``ssl_keyfile`` without ``ssl_certfile``, if ``limits`` names a
            ``max_batch_size`` that the multipart parser cannot deliver, or if the
            embedder implements no capability that version 1 serves.
    """
    if ssl_keyfile is not None and ssl_certfile is None:
        raise ValueError("ssl_keyfile was given without ssl_certfile, so TLS cannot start.")
    if not _is_loopback(host=host):
        _warn_public_bind(
            host=host, has_api_key=api_key is not None, has_tls=ssl_certfile is not None
        )
    app = create_app(embedder=embedder, api_key=api_key, limits=limits)
    uvicorn.run(app, host=host, port=port, ssl_certfile=ssl_certfile, ssl_keyfile=ssl_keyfile)


def create_app(
    embedder: Embedder,
    api_key: str | None = None,
    limits: ServerLimits | None = None,
) -> FastAPI:
    """Build the application ``serve`` runs.

    Use this function to mount the protocol in an application of your own. You can
    also use it to test an embedder with a test client and no open port.

    Args:
        embedder: The model to serve. Its capability classes set which endpoints
            exist. A text-only embedder has no image route and no video route. It
            must accept calls from more than one thread.
        api_key: The token that a client must send as
            ``Authorization: Bearer <api_key>``. The server trims the whitespace
            around the token, because a client cannot send it, and it gives a
            warning when it does.
        limits: The limits to report and to apply. The default is 999 items and
            32 MiB for each request.

    Returns:
        An application that serves ``/v1/describe`` and the capabilities of the
        embedder.

    Raises:
        ValueError: If ``api_key`` is an empty or blank string, because such a server
            looks authenticated but accepts an empty token, if ``limits`` names a
            ``max_batch_size`` that the multipart parser cannot deliver, or if the
            embedder implements no capability that version 1 serves.
    """
    if api_key is not None:
        api_key = _trimmed_api_key(api_key=api_key)
    resolved_limits = limits if limits is not None else ServerLimits()
    _check_max_batch_size(limits=resolved_limits)
    app = FastAPI(title="LightlyStudio embedding server")
    app.add_exception_handler(EmbedderContractError, _handle_contract_error)
    app.add_exception_handler(RequestValidationError, _handle_invalid_request)
    app.add_exception_handler(Exception, _handle_embedder_error)
    # The dependency enforces nothing, `BearerAuth` does. It writes the scheme into the
    # schema, so that the interactive documentation can send a token.
    security = [] if api_key is None else [Depends(HTTPBearer(auto_error=False))]
    router = APIRouter(dependencies=security)
    _mount_describe(router=router, embedder=embedder, limits=resolved_limits)
    embed_paths = _mount_embed_routes(router=router, embedder=embedder, limits=resolved_limits)
    if not embed_paths:
        served = [base.__name__ for base, _ in _SERVED_CAPABILITIES]
        raise ValueError(
            f"{type(embedder).__name__} implements no capability that version 1 serves, so "
            f"the server would have no embed endpoint. Implement one of {served}."
        )
    # Innermost first, so the server checks the token before it looks at a body at all.
    app.add_middleware(RequestSizeLimit, max_request_bytes=resolved_limits.max_request_bytes)
    app.add_middleware(Readiness, embedder=embedder, paths=embed_paths)
    if api_key is not None:
        app.add_middleware(BearerAuth, api_key=api_key, open_paths=_documentation_paths(app=app))
    app.include_router(router)
    return app


def _trimmed_api_key(api_key: str) -> str:
    """Return ``api_key`` without the whitespace around it, and warn that it went.

    ``BearerAuth`` strips the token that it reads, because RFC 7235 permits whitespace
    around the credentials of a request. A key that keeps its own whitespace therefore
    matches no token at all, and the server answers 401 to every client.
    """
    trimmed = api_key.strip()
    if not trimmed:
        raise ValueError("api_key is blank. Pass a token, or None to serve unauthenticated.")
    if trimmed != api_key:
        warnings.warn(
            "api_key has whitespace at its start or at its end. The server applies the "
            "trimmed token, because a client cannot send that whitespace.",
            stacklevel=3,
        )
    return trimmed


def _check_max_batch_size(limits: ServerLimits) -> None:
    """Reject a batch limit that the bytes endpoints cannot receive.

    The model carries no ceiling, because a client reads it from a server that can use
    another parser. This server uses the one of starlette.
    """
    if limits.max_batch_size > protocol.MAX_BATCH_SIZE_CEILING:
        raise ValueError(
            f"max_batch_size is {limits.max_batch_size}. The multipart parser of the bytes "
            f"endpoints accepts {protocol.MULTIPART_MAX_FILES} parts, so this server "
            f"advertises at most {protocol.MAX_BATCH_SIZE_CEILING}."
        )


def _is_loopback(host: str) -> bool:
    """Whether a port on ``host`` is out of reach for other hosts.

    A name other than ``localhost`` is not an address, so the answer is no. A name that
    resolves to loopback then gives a warning that it does not need, which is the safe
    side of the two.
    """
    if host == "localhost":
        return True
    try:
        return ipaddress.ip_address(host).is_loopback
    except ValueError:
        return False


def _warn_public_bind(host: str, has_api_key: bool, has_tls: bool) -> None:
    """Name every risk of an address that other hosts can reach.

    A server that has neither a token nor a certificate has two risks. It must hear about
    both now, not one of them on the next run.
    """
    risks = []
    if not has_api_key:
        risks.append(
            f"Serving on {host} without an api_key. Every host that can reach the port can "
            "use the model. Give api_key, or bind a loopback address."
        )
    if not has_tls:
        risks.append(
            f"Serving on {host} over plain HTTP. The requests, and the bearer token if you "
            "set one, go over the network in clear text. Give ssl_certfile, or end TLS at a "
            "proxy in front of the server, or bind a loopback address."
        )
    if risks:
        warnings.warn(" ".join(risks), stacklevel=3)


def _documentation_paths(app: FastAPI) -> frozenset[str]:
    """The paths of the interactive documentation, whichever of them the app mounts.

    The middleware runs before the router, so a token would gate these paths too. A
    browser puts no header on them, and they hold only the protocol, which is public.
    """
    paths = {app.openapi_url, app.docs_url, app.redoc_url, app.swagger_ui_oauth2_redirect_url}
    return frozenset(path for path in paths if path is not None)


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
