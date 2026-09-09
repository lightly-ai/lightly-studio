from __future__ import annotations

import numpy as np
from fastapi.testclient import TestClient

from lightly_studio_embed.embedder import TextEmbedder
from lightly_studio_embed.errors import CapabilityNotImplementedError
from lightly_studio_embed.protocol import ServerLimits
from lightly_studio_embed.server import create_app
from lightly_studio_embed.types import EmbeddingResult, EmbeddingSpaceSpec

SPACE_KEY = "acme/model@v1"
DIMENSION = 2


class FakeTextEmbedder(TextEmbedder):
    """Returns one fixed row per text, or a canned result when one is given."""

    def __init__(self, *, result: EmbeddingResult | None = None, ready: bool = True) -> None:
        self.result = result
        self.is_ready = ready
        self.received: list[str] = []

    def embedding_space_spec(self) -> EmbeddingSpaceSpec:
        return EmbeddingSpaceSpec(space_key=SPACE_KEY, dimension=DIMENSION)

    @property
    def ready(self) -> bool:
        return self.is_ready

    def embed_text(self, texts: list[str]) -> EmbeddingResult:
        self.received = texts
        return self.result if self.result is not None else _rows(count=len(texts))


class UnfinishedTextEmbedder(FakeTextEmbedder):
    """A mounted capability whose method was never finished."""

    def embed_text(self, texts: list[str]) -> EmbeddingResult:  # noqa: ARG002
        raise CapabilityNotImplementedError


class BrokenTextEmbedder(FakeTextEmbedder):
    """A model that fails, the way torch does for an op its backend lacks."""

    def embed_text(self, texts: list[str]) -> EmbeddingResult:
        raise NotImplementedError("could not run 'aten::foo' on the 'MPS' backend")


def _rows(*, count: int) -> EmbeddingResult:
    embeddings = np.array([[0.5, -0.5]] * count, dtype=np.float32).reshape(count, DIMENSION)
    return EmbeddingResult(embeddings=embeddings, kept_indices=list(range(count)))


def test_create_app__describe() -> None:
    client = TestClient(create_app(embedder=FakeTextEmbedder()))

    response = client.get("/v1/describe")

    assert response.status_code == 200
    assert response.json() == {
        "protocol_version": "1.0",
        "space_key": SPACE_KEY,
        "dimension": DIMENSION,
        "ready": True,
        "capabilities": ["text"],
        "limits": {"max_batch_size": 64, "max_request_bytes": 33554432},
    }


def test_create_app__describe_not_ready() -> None:
    client = TestClient(create_app(embedder=FakeTextEmbedder(ready=False)))

    response = client.get("/v1/describe")

    assert response.json()["ready"] is False


def test_create_app__embed_texts() -> None:
    embedder = FakeTextEmbedder()
    client = TestClient(create_app(embedder=embedder))

    response = client.post("/v1/embed/texts", json={"texts": ["a red car", "a blue car"]})

    assert response.status_code == 200
    assert response.json() == {
        "space_key": SPACE_KEY,
        "dimension": DIMENSION,
        "kept_indices": [0, 1],
        "embeddings": [[0.5, -0.5], [0.5, -0.5]],
    }
    assert embedder.received == ["a red car", "a blue car"]


def test_create_app__embed_texts_with_skipped_item() -> None:
    result = EmbeddingResult(embeddings=np.array([[0.5, -0.5]], dtype=np.float32), kept_indices=[1])
    client = TestClient(create_app(embedder=FakeTextEmbedder(result=result)))

    response = client.post("/v1/embed/texts", json={"texts": ["", "a red car"]})

    assert response.status_code == 200
    assert response.json()["kept_indices"] == [1]


def test_create_app__batch_over_max_batch_size() -> None:
    app = create_app(embedder=FakeTextEmbedder(), limits=ServerLimits(max_batch_size=1))
    client = TestClient(app)

    response = client.post("/v1/embed/texts", json={"texts": ["a red car", "a blue car"]})

    assert response.status_code == 413
    assert "max_batch_size" in response.json()["detail"]


def test_create_app__embed_while_not_ready() -> None:
    client = TestClient(create_app(embedder=FakeTextEmbedder(ready=False)))

    response = client.post("/v1/embed/texts", json={"texts": ["a red car"]})

    assert response.status_code == 503
    assert response.headers["Retry-After"] == "5"


def test_create_app__capability_not_implemented() -> None:
    client = TestClient(create_app(embedder=UnfinishedTextEmbedder()))

    response = client.post("/v1/embed/texts", json={"texts": ["a red car"]})

    assert response.status_code == 501


def test_create_app__model_raises_not_implemented_error() -> None:
    client = TestClient(create_app(embedder=BrokenTextEmbedder()), raise_server_exceptions=False)

    response = client.post("/v1/embed/texts", json={"texts": ["a red car"]})

    assert response.status_code == 500


def test_create_app__embedder_returns_wrong_dimension() -> None:
    result = EmbeddingResult(
        embeddings=np.array([[0.5, -0.5, 0.5]], dtype=np.float32), kept_indices=[0]
    )
    client = TestClient(create_app(embedder=FakeTextEmbedder(result=result)))

    response = client.post("/v1/embed/texts", json={"texts": ["a red car"]})

    assert response.status_code == 500
    assert "dimension 2" in response.json()["detail"]


def test_create_app__malformed_request() -> None:
    client = TestClient(create_app(embedder=FakeTextEmbedder()))

    response = client.post("/v1/embed/texts", json={"texts": "a red car"})

    assert response.status_code == 400
