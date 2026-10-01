from __future__ import annotations

import io
import logging
from collections.abc import Iterator

import numpy as np
import pytest
from lightly_studio_serve.embedder import ImageBytesEmbedder, ImagePILEmbedder
from lightly_studio_serve.protocol import ServerLimits
from lightly_studio_serve.types import EmbeddingResult, EmbeddingSpaceSpec
from PIL import Image

from lightly_studio.embed.remote import connection, image_pil_adapter, prepared_image_route
from lightly_studio.embed.remote.embedder import RemoteEmbedder
from tests.embed.remote import threaded_server
from tests.embed.remote.helpers import DIMENSION, SPACE_KEY

# Small limits, so that a test batch fills more than one request.
LIMITS = ServerLimits(max_batch_size=2, max_request_bytes=1024)


class SizeEmbedder(ImageBytesEmbedder):
    """Embeds an image as its width and height, and records the format of each image."""

    def __init__(self) -> None:
        self.formats: list[str | None] = []

    def embedding_space_spec(self) -> EmbeddingSpaceSpec:
        return EmbeddingSpaceSpec(space_key=SPACE_KEY, dimension=DIMENSION)

    def embed_image_bytes(self, images: list[bytes]) -> EmbeddingResult:
        rows = []
        for data in images:
            with Image.open(io.BytesIO(data)) as image:
                self.formats.append(image.format)
                rows.append([float(image.width), float(image.height)])
        embeddings = np.array(rows, dtype=np.float32).reshape(len(images), DIMENSION)
        return EmbeddingResult(embeddings=embeddings, kept_indices=list(range(len(images))))


@pytest.fixture(scope="module")
def server_embedder() -> SizeEmbedder:
    return SizeEmbedder()


@pytest.fixture(scope="module")
def remote(server_embedder: SizeEmbedder) -> Iterator[RemoteEmbedder]:
    """One server and one client for the tests of this module."""
    with (
        threaded_server.serve(embedder=server_embedder, limits=LIMITS) as url,
        connection.build_client(url=url) as client,
    ):
        yield RemoteEmbedder.connect(client=client)


@pytest.fixture
def adapted(remote: RemoteEmbedder, server_embedder: SizeEmbedder) -> ImagePILEmbedder:
    server_embedder.formats.clear()
    embedder = remote.with_route(route=image_pil_adapter.ImagePILRoute)
    assert isinstance(embedder, ImagePILEmbedder)
    return embedder


class TestImagePILRoute:
    def test_embed_images_pil(
        self, adapted: ImagePILEmbedder, server_embedder: SizeEmbedder
    ) -> None:
        images = [
            Image.new("RGB", (5, 4)),
            Image.new("RGB", (8, 6)),
            Image.new("RGB", (3, 3)),
        ]

        result = adapted.embed_images_pil(images=images)

        assert result.kept_indices == [0, 1, 2]
        np.testing.assert_array_equal(
            result.embeddings,
            np.array([[5.0, 4.0], [8.0, 6.0], [3.0, 3.0]], dtype=np.float32),
        )
        assert server_embedder.formats == ["JPEG", "JPEG", "JPEG"]

    def test_embed_images_pil__skips_too_large(
        self, adapted: ImagePILEmbedder, caplog: pytest.LogCaptureFixture
    ) -> None:
        # Random pixels do not compress, so the JPEG of the 64x64 image is larger than 1024 bytes
        noise = np.random.default_rng(seed=0).integers(0, 256, size=(64, 64, 3), dtype=np.uint8)
        images = [Image.fromarray(noise), Image.new("RGB", (3, 3))]

        with caplog.at_level(logging.WARNING, logger=prepared_image_route.__name__):
            result = adapted.embed_images_pil(images=images)

        assert result.kept_indices == [1]
        np.testing.assert_array_equal(result.embeddings, np.array([[3.0, 3.0]], dtype=np.float32))
        assert "Cannot embed the image at index 0 of the batch" in caplog.text

    def test_embed_images_pil__skips_unencodable(
        self, adapted: ImagePILEmbedder, caplog: pytest.LogCaptureFixture
    ) -> None:
        # JPEG cannot hold an alpha channel
        images = [Image.new("RGBA", (5, 4)), Image.new("RGB", (3, 3))]

        with caplog.at_level(logging.WARNING, logger=image_pil_adapter.__name__):
            result = adapted.embed_images_pil(images=images)

        assert result.kept_indices == [1]
        np.testing.assert_array_equal(result.embeddings, np.array([[3.0, 3.0]], dtype=np.float32))
        assert "Cannot encode the image" in caplog.text

    def test_embed_images_pil__empty(
        self, adapted: ImagePILEmbedder, server_embedder: SizeEmbedder
    ) -> None:
        result = adapted.embed_images_pil(images=[])

        assert result.kept_indices == []
        assert result.embeddings.shape == (0, DIMENSION)
        assert server_embedder.formats == []
