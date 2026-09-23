"""Serve image-bytes queries with an embedding space that has no bytes capability.

Image search in the GUI uploads an image, so it needs ``ImageBytesEmbedder``. A custom
embedder may subclass only ``ImagePILEmbedder`` or ``ImagePathEmbedder``, which would
leave image search unavailable for its space. The adapters here wrap such an embedder
and decode or store the upload for it. An embedder that subclasses
``ImageBytesEmbedder`` is always used as is.
"""

from __future__ import annotations

import io
import tempfile
from pathlib import Path

from lightly_studio_serve.embedder import (
    ImageBytesEmbedder,
    ImagePathEmbedder,
    ImagePILEmbedder,
)
from lightly_studio_serve.types import EmbeddingResult, EmbeddingSpaceSpec
from PIL import Image

from lightly_studio.core.file_outcome_report import BROKEN_IMAGE_ERRORS
from lightly_studio.embed.embedder_config import EmbedderConfig
from lightly_studio.embed.embedder_registry import EmbedderRegistry


def get_image_bytes_embedder(
    registry: EmbedderRegistry,
    space_key: str | None = None,
    config: EmbedderConfig | None = None,
) -> ImageBytesEmbedder | None:
    """Get an embedder that embeds images by bytes for the space, or None if none can.

    Prefers the space's own bytes capability. Falls back to its PIL capability, which
    costs one decode, and then to its path capability, which costs a temporary file.

    Args:
        registry: The registry the embedder is resolved from.
        space_key: The embedding space to resolve, or None for the registry default.
        config: The stored configuration of the space, used only when no embedder is
            registered for it.

    Returns:
        An embedder for the space that embeds images by bytes, or None if the space
        embeds no images at all.
    """
    bytes_embedder = registry.get_image_bytes_embedder(space_key=space_key, config=config)
    if bytes_embedder is not None:
        return bytes_embedder

    pil_embedder = registry.get_image_pil_embedder(space_key=space_key, config=config)
    if pil_embedder is not None:
        return _DecodedImageBytesEmbedder(embedder=pil_embedder)

    path_embedder = registry.get_image_path_embedder(space_key=space_key, config=config)
    if path_embedder is not None:
        return _TempFileImageBytesEmbedder(embedder=path_embedder)

    return None


class _DecodedImageBytesEmbedder(ImageBytesEmbedder):
    """Embeds images by bytes with an embedder that only embeds PIL images.

    Decodes the bytes in memory, so nothing is written to disk.
    """

    __slots__ = ("_embedder",)

    def __init__(self, embedder: ImagePILEmbedder) -> None:
        """Wrap a PIL embedder.

        Args:
            embedder: The embedder that receives the decoded images.
        """
        self._embedder = embedder

    def embedding_space_spec(self) -> EmbeddingSpaceSpec:
        """Describe the wrapped embedder's space."""
        return self._embedder.embedding_space_spec()

    @property
    def ready(self) -> bool:
        """Whether the wrapped embedder is ready."""
        return self._embedder.ready

    def embed_image_bytes(self, images: list[bytes]) -> EmbeddingResult:
        """Decode the images and embed them with the wrapped embedder.

        Args:
            images: Encoded image bytes (JPEG, PNG or WebP).

        Returns:
            The embeddings and the indices of the inputs they cover. An input that does
            not decode is skipped.
        """
        decoded: list[Image.Image] = []
        decoded_indices: list[int] = []
        for index, image_bytes in enumerate(images):
            try:
                image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
            except BROKEN_IMAGE_ERRORS:
                continue
            decoded.append(image)
            decoded_indices.append(index)

        result = self._embedder.embed_images_pil(images=decoded)
        return _result_for_source_indices(result=result, source_indices=decoded_indices)


class _TempFileImageBytesEmbedder(ImageBytesEmbedder):
    """Embeds images by bytes with an embedder that only embeds images by path.

    Writes the bytes to a temporary file, which is removed after the call. An embedder
    that cannot read a local path, such as a route to a remote server, must subclass
    ``ImageBytesEmbedder`` itself.
    """

    __slots__ = ("_embedder",)

    def __init__(self, embedder: ImagePathEmbedder) -> None:
        """Wrap a path embedder.

        Args:
            embedder: The embedder that receives the paths of the temporary files.
        """
        self._embedder = embedder

    def embedding_space_spec(self) -> EmbeddingSpaceSpec:
        """Describe the wrapped embedder's space."""
        return self._embedder.embedding_space_spec()

    @property
    def ready(self) -> bool:
        """Whether the wrapped embedder is ready."""
        return self._embedder.ready

    def embed_image_bytes(self, images: list[bytes]) -> EmbeddingResult:
        """Write the images to temporary files and embed them with the wrapped embedder.

        Args:
            images: Encoded image bytes (JPEG, PNG or WebP).

        Returns:
            The embeddings and the indices of the inputs they cover.
        """
        with tempfile.TemporaryDirectory() as directory:
            paths = [
                _write_image(directory=Path(directory), index=index, image_bytes=image_bytes)
                for index, image_bytes in enumerate(images)
            ]
            return self._embedder.embed_images(paths=paths)


def _result_for_source_indices(
    result: EmbeddingResult, source_indices: list[int]
) -> EmbeddingResult:
    """Map a result over a filtered batch back to the positions in the original batch.

    Args:
        result: Result of embedding the items at ``source_indices``, whose
            ``kept_indices`` point into that filtered batch.
        source_indices: Position in the original batch of each item that was embedded.

    Returns:
        The same embeddings with ``kept_indices`` pointing into the original batch.
    """
    return EmbeddingResult(
        embeddings=result.embeddings,
        kept_indices=[source_indices[index] for index in result.kept_indices],
    )


def _write_image(directory: Path, index: int, image_bytes: bytes) -> str:
    """Write encoded image bytes to a file named after the image's position and format.

    Args:
        directory: Directory the file is written to.
        index: Position of the image in the batch.
        image_bytes: Encoded image bytes (JPEG, PNG or WebP).

    Returns:
        The path of the written file.
    """
    filepath = directory / f"image_{index}{_image_suffix(image_bytes=image_bytes)}"
    filepath.write_bytes(image_bytes)
    return str(filepath)


def _image_suffix(image_bytes: bytes) -> str:
    """Get the file suffix for encoded image bytes, or "" if the format is unknown.

    Reads the format from the header rather than trusting the upload's file name, which
    the embedder does not see.

    Args:
        image_bytes: Encoded image bytes (JPEG, PNG or WebP).

    Returns:
        The suffix, including the leading dot, such as ``".jpeg"``.
    """
    try:
        image_format = Image.open(io.BytesIO(image_bytes)).format
    except BROKEN_IMAGE_ERRORS:
        return ""
    return "" if image_format is None else f".{image_format.lower()}"
