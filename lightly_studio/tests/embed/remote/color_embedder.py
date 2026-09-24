"""Deterministic embedders that embed an input by its color.

The ingestion embedder implements only ``ImagePathEmbedder``, so a query can only embed on
the remote server.
"""

from __future__ import annotations

import io
import threading
from collections.abc import Sequence
from pathlib import Path

import numpy as np
from lightly_studio_serve.embedder import ImageBytesEmbedder, ImagePathEmbedder, TextEmbedder
from lightly_studio_serve.types import EmbeddingResult, EmbeddingSpaceSpec
from PIL import Image

SPACE_KEY = "e2e/color@v1"
DIMENSION = 3

COLORS = {
    "red": (255, 0, 0),
    "green": (0, 255, 0),
    "blue": (0, 0, 255),
}
"""The RGB value of each color. A text query of a color name embeds to its one-hot vector."""


class ColorImagePathEmbedder(ImagePathEmbedder):
    """Embeds an image file as its mean RGB color, for ingestion."""

    def embedding_space_spec(self) -> EmbeddingSpaceSpec:
        return EmbeddingSpaceSpec(space_key=SPACE_KEY, dimension=DIMENSION)

    def embed_images(self, paths: list[str]) -> EmbeddingResult:
        return _result(rows=[_mean_color(image=Image.open(path)) for path in paths])


class ColorQueryEmbedder(TextEmbedder, ImageBytesEmbedder):
    """Embeds a color name or an image file for search, and counts the embed calls.

    A server calls the embedder from more than one thread, so a lock guards the count.
    A text that is not a color name is skipped.
    """

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._call_count = 0

    @property
    def call_count(self) -> int:
        """The number of embed calls so far, text and image together."""
        with self._lock:
            return self._call_count

    def embedding_space_spec(self) -> EmbeddingSpaceSpec:
        return EmbeddingSpaceSpec(space_key=SPACE_KEY, dimension=DIMENSION)

    def embed_text(self, texts: list[str]) -> EmbeddingResult:
        self._count()
        return _result(rows=[_color_name_vector(text=text) for text in texts])

    def embed_image_bytes(self, images: list[bytes]) -> EmbeddingResult:
        self._count()
        return _result(rows=[_mean_color(image=Image.open(io.BytesIO(image))) for image in images])

    def _count(self) -> None:
        with self._lock:
            self._call_count += 1


def write_color_images(directory: Path) -> dict[str, Path]:
    """Write one solid PNG for each color and return the path of each color."""
    paths = {}
    for name, rgb in COLORS.items():
        path = directory / f"{name}.png"
        Image.new("RGB", (8, 8), color=rgb).save(path)
        paths[name] = path
    return paths


def _mean_color(image: Image.Image) -> list[float]:
    """The mean RGB of an image, scaled to [0, 1]."""
    pixels = np.asarray(image.convert("RGB"), dtype=np.float32)
    return [float(channel) for channel in pixels.reshape(-1, DIMENSION).mean(axis=0) / 255.0]


def _color_name_vector(text: str) -> list[float] | None:
    rgb = COLORS.get(text)
    if rgb is None:
        return None
    return [channel / 255.0 for channel in rgb]


def _result(rows: Sequence[list[float] | None]) -> EmbeddingResult:
    """Keep the inputs that have a vector and skip the rest, the way an embedder does."""
    kept_indices = [index for index, row in enumerate(rows) if row is not None]
    kept_rows = [row for row in rows if row is not None]
    embeddings = np.array(kept_rows, dtype=np.float32).reshape(len(kept_indices), DIMENSION)
    return EmbeddingResult(embeddings=embeddings, kept_indices=kept_indices)
