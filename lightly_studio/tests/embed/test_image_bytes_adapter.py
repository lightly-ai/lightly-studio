"""Tests for serving image-bytes queries with a space that has no bytes capability."""

from __future__ import annotations

import io
from pathlib import Path

import numpy as np
from lightly_studio_serve.embedder import (
    ImageBytesEmbedder,
    ImagePathEmbedder,
    ImagePILEmbedder,
    TextEmbedder,
)
from lightly_studio_serve.types import EmbeddingResult, EmbeddingSpaceSpec
from PIL import Image

from lightly_studio.embed import image_bytes_adapter
from lightly_studio.embed.embedder_registry import EmbedderRegistry
from lightly_studio.embed.random_embedder import RandomEmbedder

_SPACE_KEY = "test_space"


class _FirstPixelPILEmbedder(ImagePILEmbedder):
    """Embeds each PIL image as its top-left pixel's RGB and drops the last image.

    Deriving the vector from the pixel content, not the input position, makes a test fail
    if the adapter pairs an embedding with the wrong input. A dropped input verifies that
    ``kept_indices`` of the wrapped embedder is mapped back to the original batch.
    """

    __slots__ = ()

    def embedding_space_spec(self) -> EmbeddingSpaceSpec:
        """Describe the test space with dimension 3."""
        return EmbeddingSpaceSpec(space_key=_SPACE_KEY, dimension=3)

    def embed_images_pil(self, images: list[Image.Image]) -> EmbeddingResult:
        """Embed all images but the last as their top-left RGB pixel."""
        kept_indices = list(range(len(images) - 1))
        embeddings = np.array(
            [images[index].getpixel(xy=(0, 0)) for index in kept_indices], dtype=np.float32
        )
        return EmbeddingResult(embeddings=embeddings, kept_indices=kept_indices)


class _FirstPixelPathEmbedder(ImagePathEmbedder):
    """Embeds each image read from its path as the top-left pixel's RGB.

    Records the paths it is given so a test can check the temporary files.
    """

    __slots__ = ("paths",)

    def __init__(self) -> None:
        """Create an embedder that has seen no path yet."""
        self.paths: list[str] = []

    def embedding_space_spec(self) -> EmbeddingSpaceSpec:
        """Describe the test space with dimension 3."""
        return EmbeddingSpaceSpec(space_key=_SPACE_KEY, dimension=3)

    def embed_images(self, paths: list[str]) -> EmbeddingResult:
        """Embed each image at the given path as its top-left RGB pixel."""
        self.paths = list(paths)
        embeddings = np.array(
            [Image.open(path).convert("RGB").getpixel(xy=(0, 0)) for path in paths],
            dtype=np.float32,
        )
        return EmbeddingResult(embeddings=embeddings, kept_indices=list(range(len(paths))))


class _TextOnlyEmbedder(TextEmbedder):
    """Embeds text only, so no image capability can be adapted from it."""

    __slots__ = ()

    def embedding_space_spec(self) -> EmbeddingSpaceSpec:
        """Describe the test space with dimension 3."""
        return EmbeddingSpaceSpec(space_key=_SPACE_KEY, dimension=3)

    def embed_text(self, texts: list[str]) -> EmbeddingResult:
        """Embed each text as a zero vector."""
        return EmbeddingResult(
            embeddings=np.zeros((len(texts), 3), dtype=np.float32),
            kept_indices=list(range(len(texts))),
        )


def test_get_image_bytes_embedder() -> None:
    """A space whose embedder embeds bytes is returned unwrapped."""
    embedder = RandomEmbedder()
    registry = EmbedderRegistry()
    registry.register(embedder=embedder)

    resolved = image_bytes_adapter.get_image_bytes_embedder(
        registry=registry, space_key="random_model"
    )

    assert resolved is embedder


def test_get_image_bytes_embedder__pil_only() -> None:
    """A space whose embedder embeds PIL images only is adapted by decoding the bytes."""
    registry = EmbedderRegistry()
    registry.register(embedder=_FirstPixelPILEmbedder())

    resolved = image_bytes_adapter.get_image_bytes_embedder(registry=registry, space_key=_SPACE_KEY)

    assert isinstance(resolved, ImageBytesEmbedder)
    assert resolved.embedding_space_spec() == EmbeddingSpaceSpec(space_key=_SPACE_KEY, dimension=3)


def test_get_image_bytes_embedder__path_only() -> None:
    """A space whose embedder embeds images by path only is adapted with a temporary file."""
    registry = EmbedderRegistry()
    registry.register(embedder=_FirstPixelPathEmbedder())

    resolved = image_bytes_adapter.get_image_bytes_embedder(registry=registry, space_key=_SPACE_KEY)

    assert isinstance(resolved, ImageBytesEmbedder)
    assert resolved.embedding_space_spec() == EmbeddingSpaceSpec(space_key=_SPACE_KEY, dimension=3)


def test_get_image_bytes_embedder__no_image_capability() -> None:
    """A space that embeds no image at all cannot serve an image query."""
    registry = EmbedderRegistry()
    registry.register(embedder=_TextOnlyEmbedder())

    assert (
        image_bytes_adapter.get_image_bytes_embedder(registry=registry, space_key=_SPACE_KEY)
        is None
    )


def test_get_image_bytes_embedder__unknown_space() -> None:
    """An unregistered space that is no built-in has no embedder to adapt."""
    assert (
        image_bytes_adapter.get_image_bytes_embedder(
            registry=EmbedderRegistry(), space_key="unknown_space"
        )
        is None
    )


class TestDecodedImageBytesEmbedder:
    """Tests for serving image bytes with an embedder that embeds PIL images."""

    def test_embed_image_bytes(self) -> None:
        """Every decodable image is embedded, in input order."""
        embedder = image_bytes_adapter._DecodedImageBytesEmbedder(embedder=_FirstPixelPILEmbedder())

        # The wrapped embedder drops the last input, hence the third image.
        result = embedder.embed_image_bytes(
            images=[_png_bytes(color=(1, 2, 3)), _png_bytes(color=(4, 5, 6)), _png_bytes()]
        )

        assert result.kept_indices == [0, 1]
        assert result.embeddings.tolist() == [[1.0, 2.0, 3.0], [4.0, 5.0, 6.0]]

    def test_embed_image_bytes__undecodable_skipped(self) -> None:
        """An input that is no image is skipped, and the kept indices stay aligned."""
        embedder = image_bytes_adapter._DecodedImageBytesEmbedder(embedder=_FirstPixelPILEmbedder())

        result = embedder.embed_image_bytes(
            images=[b"not an image", _png_bytes(color=(7, 8, 9)), _png_bytes()]
        )

        assert result.kept_indices == [1]
        assert result.embeddings.tolist() == [[7.0, 8.0, 9.0]]

    def test_embed_image_bytes__empty(self) -> None:
        """An empty batch embeds nothing."""
        embedder = image_bytes_adapter._DecodedImageBytesEmbedder(embedder=_FirstPixelPILEmbedder())

        assert embedder.embed_image_bytes(images=[]).kept_indices == []


class TestTempFileImageBytesEmbedder:
    """Tests for serving image bytes with an embedder that embeds images by path."""

    def test_embed_image_bytes(self) -> None:
        """Every image is written to a readable file and embedded, in input order."""
        wrapped = _FirstPixelPathEmbedder()
        embedder = image_bytes_adapter._TempFileImageBytesEmbedder(embedder=wrapped)

        result = embedder.embed_image_bytes(
            images=[_png_bytes(color=(1, 2, 3)), _png_bytes(color=(4, 5, 6))]
        )

        assert result.kept_indices == [0, 1]
        assert result.embeddings.tolist() == [[1.0, 2.0, 3.0], [4.0, 5.0, 6.0]]
        # The file name carries the format read from the data, not from the upload.
        assert [Path(path).suffix for path in wrapped.paths] == [".png", ".png"]

    def test_embed_image_bytes__temporary_files_removed(self) -> None:
        """The temporary files do not outlive the call."""
        wrapped = _FirstPixelPathEmbedder()
        embedder = image_bytes_adapter._TempFileImageBytesEmbedder(embedder=wrapped)

        embedder.embed_image_bytes(images=[_png_bytes()])

        assert not Path(wrapped.paths[0]).exists()

    def test_embed_image_bytes__empty(self) -> None:
        """An empty batch embeds nothing."""
        embedder = image_bytes_adapter._TempFileImageBytesEmbedder(
            embedder=_FirstPixelPathEmbedder()
        )

        assert embedder.embed_image_bytes(images=[]).kept_indices == []


def _png_bytes(color: tuple[int, int, int] = (0, 0, 0)) -> bytes:
    """Encode a one-pixel PNG of the given RGB color.

    Args:
        color: RGB value of the single pixel.

    Returns:
        The encoded PNG bytes.
    """
    buffer = io.BytesIO()
    Image.new(mode="RGB", size=(1, 1), color=color).save(buffer, format="PNG")
    return buffer.getvalue()
