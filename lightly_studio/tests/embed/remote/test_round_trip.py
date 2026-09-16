from __future__ import annotations

import socket
import threading
import time
import warnings

import httpx
import numpy as np
import pytest
from lightly_studio_serve import protocol, server
from lightly_studio_serve.embedder import ImageBytesEmbedder, TextEmbedder
from lightly_studio_serve.types import EmbeddingResult, EmbeddingSpaceSpec

from lightly_studio.embed.remote.embedder import RemoteEmbedder

SPACE_KEY = "acme/model@v1"
DIMENSION = 2

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

# An input that the server cannot read. It is absent from the table above, so the embedder
# skips it and keeps the rest of the batch.
BROKEN_TEXT = "not decodable"

_HOST = "127.0.0.1"

# The wait for the server to answer its first request. Generous for a loopback server, so
# that a loaded machine running the suite under xdist does not make this test flaky.
_STARTUP_TIMEOUT_SECONDS = 10.0
_POLL_INTERVAL_SECONDS = 0.02
_POLL_TIMEOUT_SECONDS = 1.0


class TableEmbedder(TextEmbedder, ImageBytesEmbedder):
    """Answers a fixed vector for each known input, and skips the ones it cannot read.

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
def server_url() -> str:
    """Serve `TableEmbedder` over a real socket and answer with its address.

    One server serves every test of this module, so the suite pays the startup once. The
    thread is a daemon, so the interpreter does not wait for it and the fixture needs no
    shutdown. `serve` runs uvicorn, which installs no signal handler off the main thread.
    """
    port = _free_port()
    thread = threading.Thread(
        target=server.serve,
        kwargs={"embedder": TableEmbedder(), "host": _HOST, "port": port},
        daemon=True,
    )
    thread.start()
    url = f"http://{_HOST}:{port}"
    _wait_until_ready(url=url)
    return url


@pytest.fixture(scope="module")
def remote(server_url: str) -> RemoteEmbedder:
    """One client for the tests that only embed. `test_connect` builds its own."""
    return RemoteEmbedder.connect(url=server_url)


class TestRoundTrip:
    def test_connect(self, server_url: str) -> None:
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            embedder = RemoteEmbedder.connect(url=server_url)

        # A loopback address is what a self-hosted customer runs, so the URL policy must
        # not warn about clear text for it.
        assert [str(warning.message) for warning in caught if _is_policy_warning(warning)] == []
        assert isinstance(embedder, TextEmbedder)
        assert isinstance(embedder, ImageBytesEmbedder)
        assert embedder.embedding_space_spec() == EmbeddingSpaceSpec(
            space_key=SPACE_KEY, dimension=DIMENSION
        )

    def test_embed_text(self, remote: RemoteEmbedder) -> None:
        result = remote.embed_text(texts=["a dog", "a cat"])

        assert result.kept_indices == [0, 1]
        assert result.embeddings.dtype == np.float32
        np.testing.assert_array_equal(
            result.embeddings, np.array([[1.0, 0.0], [0.0, 1.0]], dtype=np.float32)
        )

    def test_embed_text__skips_a_broken_item(self, remote: RemoteEmbedder) -> None:
        result = remote.embed_text(texts=["a dog", BROKEN_TEXT, "a bird"])

        assert result.kept_indices == [0, 2]
        np.testing.assert_array_equal(
            result.embeddings, np.array([[1.0, 0.0], [1.0, 1.0]], dtype=np.float32)
        )

    def test_embed_image_bytes(self, remote: RemoteEmbedder) -> None:
        result = remote.embed_image_bytes(images=[b"the first image", b"the second image"])

        assert result.kept_indices == [0, 1]
        assert result.embeddings.dtype == np.float32
        np.testing.assert_array_equal(
            result.embeddings, np.array([[2.0, 0.0], [0.0, 2.0]], dtype=np.float32)
        )

    def test_embed_text__empty(self, remote: RemoteEmbedder) -> None:
        result = remote.embed_text(texts=[])

        assert result.kept_indices == []
        assert result.embeddings.shape == (0, DIMENSION)


def _result(rows: list[list[float] | None]) -> EmbeddingResult:
    """Keep the inputs that have a vector and skip the rest, the way an embedder does."""
    kept_indices = [index for index, row in enumerate(rows) if row is not None]
    kept_rows = [row for row in rows if row is not None]
    embeddings = np.array(kept_rows, dtype=np.float32).reshape(len(kept_indices), DIMENSION)
    return EmbeddingResult(embeddings=embeddings, kept_indices=kept_indices)


def _free_port() -> int:
    """Take a port that is free now.

    The socket closes before the server binds it, so another process can take the port in
    between. That race is acceptable in a test, and closing it needs the internals of
    uvicorn. Each xdist worker calls this, so no two workers share a port.
    """
    with socket.socket() as probe:
        probe.bind((_HOST, 0))
        return int(probe.getsockname()[1])


def _wait_until_ready(url: str) -> None:
    """Poll `/v1/describe` until the server answers, then fail with what went wrong."""
    deadline = time.monotonic() + _STARTUP_TIMEOUT_SECONDS
    last_problem = "it was never reached"
    while time.monotonic() < deadline:
        try:
            response = httpx.get(f"{url}{protocol.DESCRIBE_PATH}", timeout=_POLL_TIMEOUT_SECONDS)
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


def _is_policy_warning(warning: warnings.WarningMessage) -> bool:
    """Whether a warning came from the URL policy, and not from a library underneath."""
    return issubclass(warning.category, UserWarning)
