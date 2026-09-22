"""Answers the wire by hand, for the cases that a real application cannot produce.

``create_app`` mounts the routes of the embedder it gets, so it always agrees with itself.
``FakeServer`` does not: it advertises what a test asks for and answers what a test hands
it, which is how a capability that this client ignores, vectors of another space and a 501
for an advertised route reach the embedder.
"""

from __future__ import annotations

from collections.abc import Sequence

import httpx
import numpy as np
from lightly_studio_serve import protocol
from lightly_studio_serve.embedder import (
    Embedder,
    ImageBytesEmbedder,
    TextEmbedder,
    VideoBytesEmbedder,
)
from lightly_studio_serve.types import EmbeddingResult, EmbeddingSpaceSpec
from numpy.typing import NDArray

SPACE_KEY = "acme/model@v1"
DIMENSION = 2
# Loopback, so the URL policy of `RemoteEmbedder.connect` gives no clear-text warning.
BASE_URL = "http://127.0.0.1:8080"
ROW = [0.5, -0.5]

# The paths of the protocol. A request to anything else is a routing error of this client.
_KNOWN_PATHS = frozenset(
    {
        protocol.DESCRIBE_PATH,
        protocol.EMBED_TEXTS_PATH,
        protocol.EMBED_IMAGES_BYTES_PATH,
        protocol.EMBED_VIDEOS_BYTES_PATH,
    }
)


class _FakeEmbedder(Embedder):
    """Records every batch it is handed and returns one fixed row per item.

    The subclasses below only pick the interfaces. That choice is what decides the routes
    `create_app` mounts and the capabilities `/v1/describe` advertises.
    """

    def __init__(self) -> None:
        self.batches: list[Sequence[object]] = []

    def embedding_space_spec(self) -> EmbeddingSpaceSpec:
        return EmbeddingSpaceSpec(space_key=SPACE_KEY, dimension=DIMENSION)

    def embed_text(self, texts: list[str]) -> EmbeddingResult:
        return self._record(items=texts)

    def embed_image_bytes(self, images: list[bytes]) -> EmbeddingResult:
        return self._record(items=images)

    def embed_video_bytes(self, videos: list[bytes]) -> EmbeddingResult:
        return self._record(items=videos)

    def _record(self, items: Sequence[object]) -> EmbeddingResult:
        self.batches.append(list(items))
        return rows(count=len(items))


class FakeTextEmbedder(_FakeEmbedder, TextEmbedder):
    pass


class FakeImageEmbedder(_FakeEmbedder, ImageBytesEmbedder):
    pass


class FakeVideoEmbedder(_FakeEmbedder, VideoBytesEmbedder):
    pass


class FakeTextImageEmbedder(_FakeEmbedder, TextEmbedder, ImageBytesEmbedder):
    pass


class FakeTextVideoEmbedder(_FakeEmbedder, TextEmbedder, VideoBytesEmbedder):
    pass


class SkippingTextEmbedder(_FakeEmbedder, TextEmbedder):
    """Skips the second item of every batch, the way a broken input is skipped."""

    def embed_text(self, texts: list[str]) -> EmbeddingResult:
        self.batches.append(texts.copy())
        kept_indices = [index for index in range(len(texts)) if index != 1]
        return EmbeddingResult(
            embeddings=_stack(count=len(kept_indices)), kept_indices=kept_indices
        )


class FakeServer:
    """Answers ``/v1/describe`` from a capability list, and every embed route with one response.

    Attributes:
        paths: The path of every request that arrived, in order.
        describe_calls: How many times ``/v1/describe`` was read.
    """

    def __init__(
        self,
        capabilities: list[str],
        answer: httpx.Response | None = None,
        ready: bool = True,
    ) -> None:
        self.capabilities = capabilities
        self.answer = answer
        self.ready = ready
        # Set by a test to make a later read of `/v1/describe` fail.
        self.describe_answer: httpx.Response | None = None
        self.describe_calls = 0
        self.paths: list[str] = []

    def client(self) -> httpx.Client:
        return httpx.Client(transport=httpx.MockTransport(self._handle), base_url=BASE_URL)

    def _handle(self, request: httpx.Request) -> httpx.Response:
        path = request.url.path
        # A path outside the protocol reaches no server, so a test must not pass on one.
        assert path in _KNOWN_PATHS, f"The client asked for {path!r}, which the protocol has not."
        self.paths.append(path)
        if path == protocol.DESCRIBE_PATH:
            self.describe_calls += 1
            if self.describe_answer is not None:
                return self.describe_answer
            return httpx.Response(status_code=200, json=self._describe_body())
        assert self.answer is not None
        return self.answer

    def _describe_body(self) -> dict[str, object]:
        return {
            "protocol_version": protocol.PROTOCOL_VERSION,
            "space_key": SPACE_KEY,
            "dimension": DIMENSION,
            "ready": self.ready,
            "capabilities": self.capabilities,
            "limits": {"max_batch_size": 999, "max_request_bytes": 1024},
        }


def rows(count: int) -> EmbeddingResult:
    """Build the result of an embedder that keeps every item it is handed."""
    return EmbeddingResult(embeddings=_stack(count=count), kept_indices=list(range(count)))


def embeddings_body(
    kept_indices: list[int],
    embeddings: list[list[float]],
    space_key: str = SPACE_KEY,
    dimension: int = DIMENSION,
) -> dict[str, object]:
    """Build the body that an embed route answers."""
    return {
        "space_key": space_key,
        "dimension": dimension,
        "kept_indices": kept_indices,
        "embeddings": embeddings,
    }


def _stack(count: int) -> NDArray[np.float32]:
    """Repeat ``ROW`` ``count`` times, shaped (count, DIMENSION) even when count is 0."""
    return np.tile(np.array(ROW, dtype=np.float32), (count, 1))
