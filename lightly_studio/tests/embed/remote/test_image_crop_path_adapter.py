from __future__ import annotations

import io
import logging
from collections.abc import Iterator
from pathlib import Path

import numpy as np
import pytest
from lightly_studio_serve.embedder import ImageBytesEmbedder, ImageCropPathEmbedder
from lightly_studio_serve.protocol import ServerLimits
from lightly_studio_serve.types import EmbeddingResult, EmbeddingSpaceSpec, ImageCrop
from PIL import Image
from pytest_mock import MockerFixture

from lightly_studio.embed.remote import (
    connection,
    image_crop_path_adapter,
    prepared_image_route,
)
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
def adapted(remote: RemoteEmbedder, server_embedder: SizeEmbedder) -> ImageCropPathEmbedder:
    server_embedder.formats.clear()
    embedder = remote.with_route(route=image_crop_path_adapter.ImageCropPathRoute)
    assert isinstance(embedder, ImageCropPathEmbedder)
    return embedder


class TestImageCropPathRoute:
    def test_embed_image_crops(
        self, tmp_path: Path, adapted: ImageCropPathEmbedder, server_embedder: SizeEmbedder
    ) -> None:
        path = _write_image(path=tmp_path / "a.png", width=20, height=10)
        crops = [
            ImageCrop(filepath=path, x=0, y=0, width=5, height=4),
            ImageCrop(filepath=path, x=10, y=2, width=8, height=6),
            ImageCrop(filepath=path, x=1, y=1, width=3, height=3),
        ]

        result = adapted.embed_image_crops(crops=crops)

        assert result.kept_indices == [0, 1, 2]
        # The server gets each box with no padding
        np.testing.assert_array_equal(
            result.embeddings,
            np.array([[5.0, 4.0], [8.0, 6.0], [3.0, 3.0]], dtype=np.float32),
        )
        assert server_embedder.formats == ["JPEG", "JPEG", "JPEG"]

    def test_embed_image_crops__keeps_the_input_order(
        self, tmp_path: Path, adapted: ImageCropPathEmbedder
    ) -> None:
        path_a = _write_image(path=tmp_path / "a.png", width=10, height=10)
        path_b = _write_image(path=tmp_path / "b.png", width=10, height=10)
        # The crops of one file are sent together: a, a, then b.
        crops = [
            ImageCrop(filepath=path_a, x=0, y=0, width=1, height=1),
            ImageCrop(filepath=path_b, x=0, y=0, width=2, height=2),
            ImageCrop(filepath=path_a, x=0, y=0, width=3, height=3),
        ]

        result = adapted.embed_image_crops(crops=crops)

        assert result.kept_indices == [0, 1, 2]
        np.testing.assert_array_equal(
            result.embeddings,
            np.array([[1.0, 1.0], [2.0, 2.0], [3.0, 3.0]], dtype=np.float32),
        )

    def test_embed_image_crops__skips_unreadable(
        self, tmp_path: Path, adapted: ImageCropPathEmbedder, caplog: pytest.LogCaptureFixture
    ) -> None:
        missing = str(tmp_path / "missing.png")
        path = _write_image(path=tmp_path / "a.png", width=10, height=10)
        crops = [
            ImageCrop(filepath=missing, x=0, y=0, width=2, height=2),
            ImageCrop(filepath=path, x=0, y=0, width=3, height=3),
        ]

        with caplog.at_level(logging.WARNING, logger=image_crop_path_adapter.__name__):
            result = adapted.embed_image_crops(crops=crops)

        assert result.kept_indices == [1]
        np.testing.assert_array_equal(result.embeddings, np.array([[3.0, 3.0]], dtype=np.float32))
        assert f"Cannot read the image {missing}" in caplog.text

    def test_embed_image_crops__skips_too_large(
        self, tmp_path: Path, adapted: ImageCropPathEmbedder, caplog: pytest.LogCaptureFixture
    ) -> None:
        # Random pixels do not compress, so the JPEG of the 64x64 crop is larger than 1024 bytes
        noise = np.random.default_rng(seed=0).integers(0, 256, size=(64, 64, 3), dtype=np.uint8)
        noise_path = tmp_path / "noise.png"
        Image.fromarray(noise).save(noise_path)
        path = _write_image(path=tmp_path / "a.png", width=10, height=10)
        crops = [
            ImageCrop(filepath=str(noise_path), x=0, y=0, width=64, height=64),
            ImageCrop(filepath=path, x=0, y=0, width=3, height=3),
        ]

        with caplog.at_level(logging.WARNING, logger=prepared_image_route.__name__):
            result = adapted.embed_image_crops(crops=crops)

        assert result.kept_indices == [1]
        np.testing.assert_array_equal(result.embeddings, np.array([[3.0, 3.0]], dtype=np.float32))
        assert "Cannot embed the crop" in caplog.text

    def test_embed_image_crops__skips_unencodable(
        self, tmp_path: Path, adapted: ImageCropPathEmbedder, caplog: pytest.LogCaptureFixture
    ) -> None:
        # A JPEG side can be at most 65500 pixels
        wide = _write_image(path=tmp_path / "wide.png", width=65501, height=1)
        path = _write_image(path=tmp_path / "a.png", width=10, height=10)
        crops = [
            ImageCrop(filepath=wide, x=0, y=0, width=65501, height=1),
            ImageCrop(filepath=path, x=0, y=0, width=3, height=3),
        ]

        with caplog.at_level(logging.WARNING, logger=image_crop_path_adapter.__name__):
            result = adapted.embed_image_crops(crops=crops)

        assert result.kept_indices == [1]
        np.testing.assert_array_equal(result.embeddings, np.array([[3.0, 3.0]], dtype=np.float32))
        assert "Cannot encode the crop" in caplog.text

    def test_embed_image_crops__skips_a_box_with_no_area(
        self, tmp_path: Path, adapted: ImageCropPathEmbedder
    ) -> None:
        path = _write_image(path=tmp_path / "a.png", width=10, height=10)
        crops = [
            ImageCrop(filepath=path, x=2, y=2, width=0, height=3),
            ImageCrop(filepath=path, x=0, y=0, width=3, height=3),
        ]

        result = adapted.embed_image_crops(crops=crops)

        assert result.kept_indices == [1]
        np.testing.assert_array_equal(result.embeddings, np.array([[3.0, 3.0]], dtype=np.float32))

    def test_embed_image_crops__empty(
        self, adapted: ImageCropPathEmbedder, server_embedder: SizeEmbedder
    ) -> None:
        result = adapted.embed_image_crops(crops=[])

        assert result.kept_indices == []
        assert result.embeddings.shape == (0, DIMENSION)
        assert server_embedder.formats == []


def test_encode_crops__encodes_one_crop_at_a_time(mocker: MockerFixture) -> None:
    spy = mocker.spy(image_crop_path_adapter, "_encode_crop")
    crops = [
        (index, ImageCrop(filepath="a.png", x=0, y=0, width=2, height=2)) for index in range(3)
    ]
    decoded_file = image_crop_path_adapter._DecodedFile(
        image=Image.new("RGB", (10, 10)), indexed_crops=crops
    )

    encoded = image_crop_path_adapter._encode_crops(decoded_files=[decoded_file])

    assert next(encoded)[0] == 0
    assert spy.call_count == 1
    assert [index for index, _ in encoded] == [1, 2]
    assert spy.call_count == 3


def _write_image(path: Path, width: int, height: int) -> str:
    Image.new("RGB", (width, height), color=(200, 100, 50)).save(path)
    return str(path)
