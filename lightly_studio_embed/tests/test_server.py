from __future__ import annotations

from collections.abc import Iterator

import pytest
import uvicorn
from fastapi.testclient import TestClient

from lightly_studio_embed import server
from lightly_studio_embed.embedder import (
    EmbeddingResult,
    ImageBytesEmbedder,
    TextEmbedder,
    VideoBytesEmbedder,
)
from lightly_studio_embed.errors import CapabilityNotImplementedError
from lightly_studio_embed.protocol import ServerLimits
from lightly_studio_embed.server import create_app

SPACE_KEY = "acme/model@v1"
DIMENSION = 2
_BOUNDARY = "b0undary"


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


class UnfinishedTextEmbedder(FakeTextEmbedder):
    """A mounted capability whose method was never finished."""

    def embed_text(self, texts: list[str]) -> EmbeddingResult:  # noqa: ARG002
        raise CapabilityNotImplementedError


class BrokenTextEmbedder(FakeTextEmbedder):
    """A model that fails, the way torch does for an op its backend lacks."""

    def embed_text(self, texts: list[str]) -> EmbeddingResult:
        raise NotImplementedError("could not run 'aten::foo' on the 'MPS' backend")


def _rows(*, count: int) -> EmbeddingResult:
    return EmbeddingResult(embeddings=[[0.5, -0.5]] * count, kept_indices=list(range(count)))


def _chunked_multipart() -> Iterator[bytes]:
    """One 4 MB part, streamed so that the request carries no ``Content-Length``."""
    yield (
        f'--{_BOUNDARY}\r\nContent-Disposition: form-data; name="files"; filename="a.jpg"\r\n\r\n'
    ).encode()
    yield b"x" * 4_000_000
    yield f"\r\n--{_BOUNDARY}--\r\n".encode()


def _unreadable_body() -> Iterator[bytes]:
    """A body that raises the moment anything reads it.

    Starlette answers 400 when a body fails to parse, so a request that comes back 401 is
    one whose body was never touched.
    """
    raise AssertionError("The request body was read before the bearer token was checked.")
    yield b""  # Unreachable, and only here to make this a generator.


def _do_not_run(*_args: object, **_kwargs: object) -> None:
    """Stand in for ``uvicorn.run``, so ``serve`` returns instead of binding a port."""


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
    client = TestClient(create_app(embedder=UnfinishedTextEmbedder()))

    response = client.post("/v1/embed/texts", json={"texts": ["a red car"]})

    assert response.status_code == 501


def test_create_app__model_raises_not_implemented_error() -> None:
    client = TestClient(create_app(embedder=BrokenTextEmbedder()), raise_server_exceptions=False)

    response = client.post("/v1/embed/texts", json={"texts": ["a red car"]})

    assert response.status_code == 500


def test_create_app__embedder_returns_wrong_dimension() -> None:
    result = EmbeddingResult(embeddings=[[0.5, -0.5, 0.5]], kept_indices=[0])
    client = TestClient(create_app(embedder=FakeTextEmbedder(result=result)))

    response = client.post("/v1/embed/texts", json={"texts": ["a red car"]})

    assert response.status_code == 500
    assert "dimension 2" in response.json()["detail"]


def test_create_app__non_ascii_bearer_token() -> None:
    client = TestClient(create_app(embedder=FakeTextEmbedder(), api_key="secret"))

    response = client.get("/v1/describe", headers={b"authorization": b"Bearer \xe9"})

    assert response.status_code == 401


def test_create_app__non_ascii_api_key() -> None:
    client = TestClient(create_app(embedder=FakeTextEmbedder(), api_key="sécret"))

    response = client.get("/v1/describe", headers={b"authorization": "Bearer sécret".encode()})

    assert response.status_code == 200


def test_create_app__blank_api_key() -> None:
    with pytest.raises(ValueError, match="api_key is blank"):
        create_app(embedder=FakeTextEmbedder(), api_key=" ")


def test_create_app__chunked_body_over_max_request_bytes() -> None:
    app = create_app(embedder=FakeBytesEmbedder(), limits=ServerLimits(max_request_bytes=8))
    client = TestClient(app)

    response = client.post(
        "/v1/embed/images/bytes",
        content=_chunked_multipart(),
        headers={"Content-Type": f"multipart/form-data; boundary={_BOUNDARY}"},
    )

    assert response.request.headers["transfer-encoding"] == "chunked"
    assert response.status_code == 413
    assert "max_request_bytes" in response.json()["detail"]


def test_create_app__unauthenticated_request_body_is_never_read() -> None:
    """The token is checked first: reading this body would answer 400 instead of 401."""
    client = TestClient(create_app(embedder=FakeBytesEmbedder(), api_key="secret"))

    response = client.post(
        "/v1/embed/images/bytes",
        content=_unreadable_body(),
        headers={"Content-Type": f"multipart/form-data; boundary={_BOUNDARY}"},
    )

    assert response.status_code == 401


def test_create_app__malformed_request() -> None:
    client = TestClient(create_app(embedder=FakeTextEmbedder()))

    response = client.post("/v1/embed/texts", json={"texts": "a red car"})

    assert response.status_code == 400


def test_serve__warns_on_a_public_bind_without_a_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(uvicorn, "run", _do_not_run)

    with pytest.warns(UserWarning, match="without an api_key"):
        server.serve(FakeTextEmbedder(), host="0.0.0.0")


def test_serve__silent_on_a_loopback_bind(
    monkeypatch: pytest.MonkeyPatch, recwarn: pytest.WarningsRecorder
) -> None:
    monkeypatch.setattr(uvicorn, "run", _do_not_run)

    server.serve(FakeTextEmbedder())

    assert len(recwarn) == 0
