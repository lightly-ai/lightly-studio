from __future__ import annotations

import numpy as np
import pytest
from fastapi.testclient import TestClient

from lightly_studio_serve.embedder import (
    ImageBytesEmbedder,
    ImagePathEmbedder,
    TextEmbedder,
    VideoBytesEmbedder,
)
from lightly_studio_serve.protocol import ServerLimits
from lightly_studio_serve.server import create_app
from lightly_studio_serve.types import EmbeddingResult, EmbeddingSpaceSpec

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


class FakeBytesEmbedder(ImageBytesEmbedder, VideoBytesEmbedder):
    """Embeds images and videos, recording the bytes it was handed."""

    def __init__(self, *, ready: bool = True) -> None:
        self.is_ready = ready
        self.received: list[bytes] = []

    def embedding_space_spec(self) -> EmbeddingSpaceSpec:
        return EmbeddingSpaceSpec(space_key=SPACE_KEY, dimension=DIMENSION)

    @property
    def ready(self) -> bool:
        return self.is_ready

    def embed_image_bytes(self, images: list[bytes]) -> EmbeddingResult:
        self.received = images
        return _rows(count=len(images))

    def embed_video_bytes(self, videos: list[bytes]) -> EmbeddingResult:
        self.received = videos
        return _rows(count=len(videos))


class BrokenTextEmbedder(FakeTextEmbedder):
    """A model that fails, the way torch does for an op its backend lacks."""

    def embed_text(self, texts: list[str]) -> EmbeddingResult:
        raise NotImplementedError("could not run 'aten::foo' on the 'MPS' backend")


class LoadingEmbedder(FakeTextEmbedder):
    """A model that reads its embedding space from a checkpoint it has not read yet."""

    def __init__(self) -> None:
        super().__init__(ready=False)

    def embedding_space_spec(self) -> EmbeddingSpaceSpec:
        raise RuntimeError("The checkpoint is not read yet.")


class PathOnlyEmbedder(ImagePathEmbedder):
    """A model that only reads paths. Version 1 carries no path over the wire."""

    def embedding_space_spec(self) -> EmbeddingSpaceSpec:
        return EmbeddingSpaceSpec(space_key=SPACE_KEY, dimension=DIMENSION)

    def embed_images(self, paths: list[str]) -> EmbeddingResult:
        return _rows(count=len(paths))


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
        "limits": {"max_batch_size": 1024, "max_request_bytes": 33554432},
    }


def test_create_app__describe_bytes_capabilities() -> None:
    client = TestClient(create_app(embedder=FakeBytesEmbedder()))

    response = client.get("/v1/describe")

    assert response.json()["capabilities"] == ["image_bytes", "video_bytes"]


def test_create_app__describe_not_ready() -> None:
    client = TestClient(create_app(embedder=FakeTextEmbedder(ready=False)))

    response = client.get("/v1/describe")

    assert response.json()["ready"] is False


def test_create_app__describe_while_the_model_loads() -> None:
    """The endpoint that a client polls must answer before the space is known."""
    client = TestClient(create_app(embedder=LoadingEmbedder()))

    response = client.get("/v1/describe")

    assert response.status_code == 200
    assert response.json()["ready"] is False
    assert response.json()["space_key"] is None
    assert response.json()["dimension"] is None


def test_create_app__embedder_without_a_served_capability() -> None:
    """A server that mounts no embed endpoint answers 404 on every path a client knows."""
    with pytest.raises(ValueError, match="no capability that version 1 serves"):
        create_app(embedder=PathOnlyEmbedder())


def test_create_app__text_only_mounts_no_other_route() -> None:
    client = TestClient(create_app(embedder=FakeTextEmbedder()))

    assert client.post("/v1/embed/images/bytes", files={"files": b"\xff\xd8"}).status_code == 404
    assert client.post("/v1/embed/videos/bytes", files={"files": b"\x00\x00"}).status_code == 404


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


def test_create_app__embed_images_bytes() -> None:
    embedder = FakeBytesEmbedder()
    client = TestClient(create_app(embedder=embedder))

    response = client.post(
        "/v1/embed/images/bytes",
        files=[
            ("files", ("a.jpg", b"\xff\xd8a", "image/jpeg")),
            ("files", ("b.png", b"\x89P", "image/png")),
        ],
    )

    assert response.status_code == 200
    assert response.json()["kept_indices"] == [0, 1]
    assert embedder.received == [b"\xff\xd8a", b"\x89P"]


def test_create_app__embed_videos_bytes() -> None:
    embedder = FakeBytesEmbedder()
    client = TestClient(create_app(embedder=embedder))

    response = client.post("/v1/embed/videos/bytes", files=[("files", ("a.mp4", b"\x00moov"))])

    assert response.status_code == 200
    assert embedder.received == [b"\x00moov"]


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


def test_create_app__embed_bytes_while_not_ready() -> None:
    """The 503 comes before the parser spools the upload. It carries the same body."""
    client = TestClient(create_app(embedder=FakeBytesEmbedder(ready=False)))

    response = client.post("/v1/embed/images/bytes", files=[("files", ("a.jpg", b"\xff\xd8a"))])

    assert response.status_code == 503
    assert response.headers["Retry-After"] == "5"
    assert response.json()["detail"] == "The model is still loading."


def test_create_app__model_raises_not_implemented_error() -> None:
    """Every 500 carries a JSON ``detail``, and none of them carries the model's message."""
    client = TestClient(create_app(embedder=BrokenTextEmbedder()), raise_server_exceptions=False)

    response = client.post("/v1/embed/texts", json={"texts": ["a red car"]})

    assert response.status_code == 500
    assert response.json()["detail"] == (
        "The embedder raised NotImplementedError. See the server log."
    )
    assert "MPS" not in response.text


def test_create_app__embedder_returns_wrong_dimension() -> None:
    result = EmbeddingResult(
        embeddings=np.array([[0.5, -0.5, 0.5]], dtype=np.float32), kept_indices=[0]
    )
    client = TestClient(create_app(embedder=FakeTextEmbedder(result=result)))

    response = client.post("/v1/embed/texts", json={"texts": ["a red car"]})

    assert response.status_code == 500
    assert "dimension 2" in response.json()["detail"]
    # The broken result of the embedder stays in this process.
    assert "0.5" not in response.text


def test_create_app__malformed_request() -> None:
    client = TestClient(create_app(embedder=FakeTextEmbedder()))

    response = client.post("/v1/embed/texts", json={"texts": "a red car"})

    assert response.status_code == 400
    assert response.json()["detail"][0]["loc"] == ["body", "texts"]


def test_create_app__malformed_request_does_not_echo_the_request() -> None:
    """The client sent the value. A 400 names the rule that it broke, not the value."""
    client = TestClient(create_app(embedder=FakeTextEmbedder()))

    response = client.post("/v1/embed/texts", json={"texts": [{"secret": "abc"}]})

    assert response.status_code == 400
    assert "secret" not in response.text
    assert all("input" not in error for error in response.json()["detail"])
