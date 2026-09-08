from __future__ import annotations

from fastapi.testclient import TestClient

from lightly_studio_embed.embedder import (
    EmbeddingResult,
    ImageBytesEmbedder,
    TextEmbedder,
    VideoBytesEmbedder,
)
from lightly_studio_embed.protocol import ServerLimits
from lightly_studio_embed.server import create_app

SPACE_KEY = "acme/model@v1"
DIMENSION = 2


class FakeTextEmbedder(TextEmbedder):
    """Returns one fixed row per text, or a canned result when one is given."""

    def __init__(self, *, result: EmbeddingResult | None = None, ready: bool = True) -> None:
        self.result = result
        self.is_ready = ready
        self.received: list[str] = []

    @property
    def space_key(self) -> str:
        return SPACE_KEY

    @property
    def dimension(self) -> int:
        return DIMENSION

    @property
    def ready(self) -> bool:
        return self.is_ready

    def embed_text(self, texts: list[str]) -> EmbeddingResult:
        self.received = texts
        return self.result if self.result is not None else _rows(count=len(texts))


class FakeBytesEmbedder(ImageBytesEmbedder, VideoBytesEmbedder):
    """Embeds images and videos, recording the bytes it was handed."""

    def __init__(self) -> None:
        self.received: list[bytes] = []

    @property
    def space_key(self) -> str:
        return SPACE_KEY

    @property
    def dimension(self) -> int:
        return DIMENSION

    def embed_image_bytes(self, images: list[bytes]) -> EmbeddingResult:
        self.received = images
        return _rows(count=len(images))

    def embed_video_bytes(self, videos: list[bytes]) -> EmbeddingResult:
        self.received = videos
        return _rows(count=len(videos))


class UnimplementedTextEmbedder(FakeTextEmbedder):
    """A mounted capability whose method was never finished."""

    def embed_text(self, texts: list[str]) -> EmbeddingResult:
        raise NotImplementedError


def _rows(*, count: int) -> EmbeddingResult:
    return EmbeddingResult(embeddings=[[0.5, -0.5]] * count, kept_indices=list(range(count)))


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


def test_create_app__describe_bytes_capabilities() -> None:
    client = TestClient(create_app(embedder=FakeBytesEmbedder()))

    response = client.get("/v1/describe")

    assert response.json()["capabilities"] == ["image_bytes", "video_bytes"]


def test_create_app__describe_not_ready() -> None:
    client = TestClient(create_app(embedder=FakeTextEmbedder(ready=False)))

    response = client.get("/v1/describe")

    assert response.json()["ready"] is False


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
    result = EmbeddingResult(embeddings=[[0.5, -0.5]], kept_indices=[1])
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


def test_create_app__body_over_max_request_bytes() -> None:
    app = create_app(embedder=FakeTextEmbedder(), limits=ServerLimits(max_request_bytes=8))
    client = TestClient(app)

    response = client.post("/v1/embed/texts", json={"texts": ["a red car"]})

    assert response.status_code == 413
    assert "max_request_bytes" in response.json()["detail"]


def test_create_app__missing_bearer_token() -> None:
    client = TestClient(create_app(embedder=FakeTextEmbedder(), api_key="secret"))

    assert client.get("/v1/describe").status_code == 401


def test_create_app__wrong_bearer_token() -> None:
    client = TestClient(create_app(embedder=FakeTextEmbedder(), api_key="secret"))

    response = client.get("/v1/describe", headers={"Authorization": "Bearer wrong"})

    assert response.status_code == 401


def test_create_app__correct_bearer_token() -> None:
    client = TestClient(create_app(embedder=FakeTextEmbedder(), api_key="secret"))

    response = client.get("/v1/describe", headers={"Authorization": "Bearer secret"})

    assert response.status_code == 200


def test_create_app__no_api_key_leaves_the_server_open() -> None:
    client = TestClient(create_app(embedder=FakeTextEmbedder()))

    assert client.get("/v1/describe").status_code == 200


def test_create_app__embed_while_not_ready() -> None:
    client = TestClient(create_app(embedder=FakeTextEmbedder(ready=False)))

    response = client.post("/v1/embed/texts", json={"texts": ["a red car"]})

    assert response.status_code == 503
    assert response.headers["Retry-After"] == "5"


def test_create_app__capability_not_implemented() -> None:
    client = TestClient(create_app(embedder=UnimplementedTextEmbedder()))

    response = client.post("/v1/embed/texts", json={"texts": ["a red car"]})

    assert response.status_code == 501


def test_create_app__embedder_returns_wrong_dimension() -> None:
    result = EmbeddingResult(embeddings=[[0.5, -0.5, 0.5]], kept_indices=[0])
    client = TestClient(create_app(embedder=FakeTextEmbedder(result=result)))

    response = client.post("/v1/embed/texts", json={"texts": ["a red car"]})

    assert response.status_code == 500
    assert "dimension 2" in response.json()["detail"]
