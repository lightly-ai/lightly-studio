"""What the conformance tests need to stand a server up in this process."""

from __future__ import annotations

import contextlib
import json
import threading
import time
from collections.abc import Iterator
from typing import Any

import numpy as np
import uvicorn
from fastapi import FastAPI, Response
from fastapi.testclient import TestClient

from lightly_studio_serve import protocol
from lightly_studio_serve.conformance.client import ProbeResponse
from lightly_studio_serve.embedder import ImageBytesEmbedder, TextEmbedder, VideoBytesEmbedder
from lightly_studio_serve.types import EmbeddingResult, EmbeddingSpaceSpec

SPACE_KEY = "acme/model@v1"
DIMENSION = 2

# How long a test waits for a server to bind its port.
_STARTUP_TIMEOUT_SECONDS = 10.0

# How long a test waits for a server to let go of its port.
_SHUTDOWN_TIMEOUT_SECONDS = 10.0


class AppProbeClient:
    """Sends the probes to an application in this process, so a run opens no port."""

    def __init__(self, app: FastAPI, api_key: str | None = None) -> None:
        headers = {} if api_key is None else {"Authorization": f"Bearer {api_key}"}
        self.client = TestClient(app, headers=headers)

    # The client sends to this process, so there is nothing for a timeout to cut short.
    def get(self, path: str, timeout: float) -> ProbeResponse:
        response = self.client.get(path)
        return ProbeResponse(status_code=response.status_code, body=response.content)

    def post(self, path: str, content_type: str, body: bytes, timeout: float) -> ProbeResponse:
        response = self.client.post(path, content=body, headers={"Content-Type": content_type})
        return ProbeResponse(status_code=response.status_code, body=response.content)


class FakeEmbedder(TextEmbedder, ImageBytesEmbedder, VideoBytesEmbedder):
    """Serves every capability that version 1 mounts, with one fixed row per item."""

    def __init__(self, ready: bool = True) -> None:
        self.is_ready = ready

    def embedding_space_spec(self) -> EmbeddingSpaceSpec:
        return EmbeddingSpaceSpec(space_key=SPACE_KEY, dimension=DIMENSION)

    @property
    def ready(self) -> bool:
        return self.is_ready

    def embed_text(self, texts: list[str]) -> EmbeddingResult:
        return _rows(count=len(texts))

    def embed_image_bytes(self, images: list[bytes]) -> EmbeddingResult:
        return _rows(count=len(images))

    def embed_video_bytes(self, videos: list[bytes]) -> EmbeddingResult:
        return _rows(count=len(videos))


class FakeTextEmbedder(TextEmbedder):
    """Serves text only, so the report has a capability that is not advertised."""

    def embedding_space_spec(self) -> EmbeddingSpaceSpec:
        return EmbeddingSpaceSpec(space_key=SPACE_KEY, dimension=DIMENSION)

    def embed_text(self, texts: list[str]) -> EmbeddingResult:
        return _rows(count=len(texts))


def canned_app(describe: dict[str, Any], embeddings: dict[str, Any] | None = None) -> FastAPI:
    """Build a server that answers fixed bodies, the way a broken implementation does.

    ``embeddings=None`` mounts no embed route, the way a server that advertises a
    capability it does not serve behaves.
    """
    app = FastAPI()

    @app.get(protocol.DESCRIBE_PATH)
    def describe_route() -> Response:
        return _json_response(body=describe)

    if embeddings is not None:

        @app.post(protocol.EMBED_TEXTS_PATH)
        def embed_route() -> Response:
            return _json_response(body=embeddings)

    return app


def describe_body(**overrides: Any) -> dict[str, Any]:
    """The body of a correct ``/v1/describe``, with the fields a test changes."""
    body: dict[str, Any] = {
        "protocol_version": protocol.PROTOCOL_VERSION,
        "space_key": SPACE_KEY,
        "dimension": DIMENSION,
        "ready": True,
        "capabilities": ["text"],
        "limits": {"max_batch_size": 8, "max_request_bytes": 1024},
    }
    body.update(overrides)
    return body


def embeddings_body(**overrides: Any) -> dict[str, Any]:
    """The body of a correct embed answer, with the fields a test changes."""
    body: dict[str, Any] = {
        "space_key": SPACE_KEY,
        "dimension": DIMENSION,
        "kept_indices": [0],
        "embeddings": [[0.5, -0.5]],
    }
    body.update(overrides)
    return body


@contextlib.contextmanager
def serving(app: FastAPI) -> Iterator[str]:
    """Run ``app`` on a loopback port and yield its address. The real client needs a socket."""
    server = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=0, log_level="warning"))
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{_bound_port(server=server)}"
    finally:
        server.should_exit = True
        thread.join(timeout=_SHUTDOWN_TIMEOUT_SECONDS)
        assert not thread.is_alive(), "The server kept its port, so a later test may fail."


def _bound_port(server: uvicorn.Server) -> int:
    """Wait until the server binds, and name the port it got."""
    deadline = time.monotonic() + _STARTUP_TIMEOUT_SECONDS
    while not server.started:
        if time.monotonic() > deadline:
            raise TimeoutError("The server did not bind a port.")
        time.sleep(0.01)
    port: int = server.servers[0].sockets[0].getsockname()[1]
    return port


def _json_response(body: dict[str, Any]) -> Response:
    """Serialize with the standard library, which writes ``NaN`` the way a server can."""
    return Response(content=json.dumps(body), media_type="application/json")


def _rows(count: int) -> EmbeddingResult:
    embeddings = np.array([[0.5, -0.5]] * count, dtype=np.float32).reshape(count, DIMENSION)
    return EmbeddingResult(embeddings=embeddings, kept_indices=list(range(count)))
