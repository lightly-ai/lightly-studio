from __future__ import annotations

import socket
import threading
import time
from collections.abc import Iterator, Sequence

import httpx
import numpy as np
import pytest
import uvicorn
from lightly_studio_serve import protocol, server
from lightly_studio_serve.embedder import ImageBytesEmbedder, TextEmbedder
from lightly_studio_serve.types import EmbeddingResult, EmbeddingSpaceSpec

from lightly_studio.embed.remote import connection
from lightly_studio.embed.remote.embedder import RemoteEmbedder
from tests.embed.remote.helpers import DIMENSION, SPACE_KEY

# The vector that the server answers for each input. A table keeps the assertions
# readable: a round trip has to give back exactly these rows, in this order.
TEXT_VECTORS = {
    "a dog": [1.0, 0.0],
    "a cat": [0.0, 1.0],
    "a bird": [1.0, 1.0],
}

IMAGE_VECTORS = {
    b"the first image": [2.0, 0.0],
    b"the second image": [0.0, 2.0],
}

# An input that the tables above do not hold, so the embedder skips it and keeps the rest
# of the batch.
UNKNOWN_TEXT = "an unknown text"

_HOST = "127.0.0.1"

# The wait for the server to answer its first request. Generous for a loopback server, so
# that a loaded machine running the suite under xdist does not make this test flaky.
_STARTUP_TIMEOUT_SECONDS = 10.0
_POLL_INTERVAL_SECONDS = 0.02
_POLL_TIMEOUT_SECONDS = 1.0


class TableEmbedder(TextEmbedder, ImageBytesEmbedder):
    """Answers a fixed vector for each known input, and skips the rest.

    An embedder skips a broken input instead of failing the batch, so an input that the
    tables do not hold stands for that case.
    """

    def embedding_space_spec(self) -> EmbeddingSpaceSpec:
        return EmbeddingSpaceSpec(space_key=SPACE_KEY, dimension=DIMENSION)

    def embed_text(self, texts: list[str]) -> EmbeddingResult:
        return _result(rows=[TEXT_VECTORS.get(text) for text in texts])

    def embed_image_bytes(self, images: list[bytes]) -> EmbeddingResult:
        return _result(rows=[IMAGE_VECTORS.get(image) for image in images])


@pytest.fixture(scope="module")
def server_url() -> Iterator[str]:
    """Serve `TableEmbedder` over a real socket and answer with its address.

    One server serves every test of this module on a worker, so the suite pays the startup
    once per worker rather than once per test. The fixture binds the socket before it
    starts uvicorn, so another worker cannot claim the selected port in between.
    """
    listener = socket.socket()
    listener.bind((_HOST, 0))
    listener.listen()
    port = int(listener.getsockname()[1])
    app = server.create_app(embedder=TableEmbedder())
    uvicorn_server = uvicorn.Server(uvicorn.Config(app=app, log_level="warning"))
    thread = threading.Thread(
        target=uvicorn_server.run,
        kwargs={"sockets": [listener]},
        daemon=True,
    )
    thread.start()
    # A startup that fails still has to stop the server, or its thread serves on through
    # every later module of this worker.
    try:
        url = f"http://{_HOST}:{port}"
        _wait_until_ready(url=url)
        yield url
    finally:
        uvicorn_server.should_exit = True
        thread.join(timeout=_STARTUP_TIMEOUT_SECONDS)
        listener.close()


@pytest.fixture(scope="module")
def remote(server_url: str) -> Iterator[RemoteEmbedder]:
    """One client for the tests that only embed. `test_connect` builds its own."""
    with connection.build_client(url=server_url) as client:
        yield RemoteEmbedder.connect(client=client)


class TestRoundTrip:
    def test_connect(self, server_url: str) -> None:
        with connection.build_client(url=server_url) as client:
            embedder = RemoteEmbedder.connect(client=client)

            assert isinstance(embedder, TextEmbedder)
            assert isinstance(embedder, ImageBytesEmbedder)
            assert embedder.embedding_space_spec() == EmbeddingSpaceSpec(
                space_key=SPACE_KEY, dimension=DIMENSION
            )

    def test_embed_text(self, remote: TextEmbedder) -> None:
        result = remote.embed_text(texts=["a dog", "a cat"])

        assert result.kept_indices == [0, 1]
        assert result.embeddings.dtype == np.float32
        np.testing.assert_array_equal(
            result.embeddings, np.array([[1.0, 0.0], [0.0, 1.0]], dtype=np.float32)
        )

    def test_embed_text__skips_a_broken_item(self, remote: TextEmbedder) -> None:
        result = remote.embed_text(texts=["a dog", UNKNOWN_TEXT, "a bird"])

        assert result.kept_indices == [0, 2]
        np.testing.assert_array_equal(
            result.embeddings, np.array([[1.0, 0.0], [1.0, 1.0]], dtype=np.float32)
        )

    def test_embed_text__empty(self, remote: TextEmbedder) -> None:
        result = remote.embed_text(texts=[])

        assert result.kept_indices == []
        assert result.embeddings.shape == (0, DIMENSION)

    def test_embed_image_bytes(self, remote: ImageBytesEmbedder) -> None:
        result = remote.embed_image_bytes(images=[b"the first image", b"the second image"])

        assert result.kept_indices == [0, 1]
        assert result.embeddings.dtype == np.float32
        np.testing.assert_array_equal(
            result.embeddings, np.array([[2.0, 0.0], [0.0, 2.0]], dtype=np.float32)
        )


def _result(rows: Sequence[list[float] | None]) -> EmbeddingResult:
    """Keep the inputs that have a vector and skip the rest, the way an embedder does."""
    kept_indices = [index for index, row in enumerate(rows) if row is not None]
    kept_rows = [row for row in rows if row is not None]
    embeddings = np.array(kept_rows, dtype=np.float32).reshape(len(kept_indices), DIMENSION)
    return EmbeddingResult(embeddings=embeddings, kept_indices=kept_indices)


def _wait_until_ready(url: str) -> None:
    """Poll `/v1/describe` until the server answers, then fail with what went wrong."""
    deadline = time.monotonic() + _STARTUP_TIMEOUT_SECONDS
    last_problem = "it was never reached"
    while time.monotonic() < deadline:
        try:
            response = httpx.get(
                url=f"{url}{protocol.DESCRIBE_PATH}", timeout=_POLL_TIMEOUT_SECONDS
            )
        except httpx.HTTPError as error:
            last_problem = f"{type(error).__name__}: {error}"
        else:
            if response.status_code == httpx.codes.OK:
                return
            last_problem = f"it answered {response.status_code}"
        time.sleep(_POLL_INTERVAL_SECONDS)
    pytest.fail(
        f"The embedding server at {url} did not serve {protocol.DESCRIBE_PATH} within "
        f"{_STARTUP_TIMEOUT_SECONDS} seconds: {last_problem}."
    )
