from __future__ import annotations

import logging
from collections.abc import Iterator
from pathlib import Path

import numpy as np
import pytest
from lightly_studio_serve.embedder import ImageBytesEmbedder, ImagePathEmbedder
from lightly_studio_serve.protocol import ServerLimits
from lightly_studio_serve.types import EmbeddingResult, EmbeddingSpaceSpec

from lightly_studio.embed.remote import connection, image_path_adapter
from lightly_studio.embed.remote.embedder import RemoteEmbedder
from tests.embed.remote import threaded_server
from tests.embed.remote.helpers import DIMENSION, SPACE_KEY

# Small limits, so that a test batch fills more than one request.
LIMITS = ServerLimits(max_batch_size=2, max_request_bytes=1024)


class LengthEmbedder(ImageBytesEmbedder):
    """Embeds an image as its length in bytes, and records each batch of images."""

    def __init__(self) -> None:
        self.batches: list[list[bytes]] = []

    def embedding_space_spec(self) -> EmbeddingSpaceSpec:
        return EmbeddingSpaceSpec(space_key=SPACE_KEY, dimension=DIMENSION)

    def embed_image_bytes(self, images: list[bytes]) -> EmbeddingResult:
        self.batches.append(images.copy())
        embeddings = np.array(
            [[float(len(image)), 0.0] for image in images], dtype=np.float32
        ).reshape(len(images), DIMENSION)
        return EmbeddingResult(embeddings=embeddings, kept_indices=list(range(len(images))))


@pytest.fixture(scope="module")
def server_embedder() -> LengthEmbedder:
    return LengthEmbedder()


@pytest.fixture(scope="module")
def remote(server_embedder: LengthEmbedder) -> Iterator[RemoteEmbedder]:
    """One server and one client for the tests of this module."""
    with (
        threaded_server.serve(embedder=server_embedder, limits=LIMITS) as url,
        connection.build_client(url=url) as client,
    ):
        yield RemoteEmbedder.connect(client=client)


@pytest.fixture
def adapted(remote: RemoteEmbedder, server_embedder: LengthEmbedder) -> ImagePathEmbedder:
    server_embedder.batches.clear()
    embedder = remote.with_route(route=image_path_adapter.ImagePathRoute)
    assert isinstance(embedder, ImagePathEmbedder)
    return embedder


class TestImagePathRoute:
    def test_embed_images(
        self, tmp_path: Path, adapted: ImagePathEmbedder, server_embedder: LengthEmbedder
    ) -> None:
        paths = [
            _write(path=tmp_path / "a.png", data=b"a" * 10),
            _write(path=tmp_path / "b.png", data=b"b" * 20),
            _write(path=tmp_path / "c.png", data=b"c" * 30),
        ]

        result = adapted.embed_images(paths=paths)

        assert result.kept_indices == [0, 1, 2]
        np.testing.assert_array_equal(
            result.embeddings,
            np.array([[10.0, 0.0], [20.0, 0.0], [30.0, 0.0]], dtype=np.float32),
        )
        # One request holds at most `max_batch_size` images.
        assert server_embedder.batches == [[b"a" * 10, b"b" * 20], [b"c" * 30]]

    def test_embed_images__skips_unreadable_and_too_large(
        self, tmp_path: Path, adapted: ImagePathEmbedder, caplog: pytest.LogCaptureFixture
    ) -> None:
        missing = str(tmp_path / "missing.png")
        too_large = _write(path=tmp_path / "large.png", data=b"l" * LIMITS.max_request_bytes)
        paths = [
            _write(path=tmp_path / "a.png", data=b"a" * 10),
            missing,
            too_large,
            _write(path=tmp_path / "b.png", data=b"b" * 20),
        ]

        with caplog.at_level(logging.WARNING, logger=image_path_adapter.__name__):
            result = adapted.embed_images(paths=paths)

        assert result.kept_indices == [0, 3]
        np.testing.assert_array_equal(
            result.embeddings, np.array([[10.0, 0.0], [20.0, 0.0]], dtype=np.float32)
        )
        assert f"Cannot read the image {missing}" in caplog.text
        assert f"Cannot embed the image {too_large}" in caplog.text

    def test_embed_images__empty(
        self, adapted: ImagePathEmbedder, server_embedder: LengthEmbedder
    ) -> None:
        result = adapted.embed_images(paths=[])

        assert result.kept_indices == []
        assert result.embeddings.shape == (0, DIMENSION)
        assert server_embedder.batches == []


def _write(path: Path, data: bytes) -> str:
    path.write_bytes(data)
    return str(path)
