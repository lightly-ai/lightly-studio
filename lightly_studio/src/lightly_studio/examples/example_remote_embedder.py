"""Example of search through an embedder on a remote server.

The example has two parts:

1. A server. ``lightly_studio_serve.serve`` serves ``ColorServerEmbedder`` in a
   subprocess. In production this runs on the machine that holds the model.
2. LightlyStudio. The dataset fills the embedding space at ingestion with
   ``ColorPathEmbedder``, then ``ls.register_remote_embedder`` points the space at the
   server. Text and image search in the GUI then embed the query on the server.

Both embedders map an image to its mean color, so the example runs on CPU and downloads
no model. Search for "red", "green", "blue" or "white", or paste an image.

The local embedder embeds only image paths. An embedder registered in this process
for the space serves its own capabilities first, so a local ``TextEmbedder`` would
answer text search instead of the server.
"""

from __future__ import annotations

import io
import multiprocessing
import secrets
import time

import httpx
import lightly_studio_serve
import numpy as np
from environs import Env
from lightly_studio_serve import protocol
from lightly_studio_serve.embedder import ImageBytesEmbedder, ImagePathEmbedder, TextEmbedder
from numpy.typing import NDArray
from PIL import Image

import lightly_studio as ls
from lightly_studio.database import db_manager

SPACE_KEY = "example/mean-color@v1"
EMBEDDING_DIMENSION = 3
SERVER_PORT = 8080
SERVER_URL = f"http://127.0.0.1:{SERVER_PORT}"
SERVER_STARTUP_TIMEOUT_SECONDS = 30.0

COLOR_VECTORS = {
    "red": [1.0, 0.0, 0.0],
    "green": [0.0, 1.0, 0.0],
    "blue": [0.0, 0.0, 1.0],
    "white": [1.0, 1.0, 1.0],
}


class ColorPathEmbedder(ImagePathEmbedder):
    """Embeds images by path at ingestion. Runs in the LightlyStudio process."""

    def embedding_space_spec(self) -> ls.EmbeddingSpaceSpec:
        """Describe the shared mean-color space."""
        return ls.EmbeddingSpaceSpec(space_key=SPACE_KEY, dimension=EMBEDDING_DIMENSION)

    def embed_images(self, paths: list[str]) -> ls.EmbeddingResult:
        """Embed each image file as its mean color."""
        return _result(rows=[_mean_color(image=Image.open(path)) for path in paths])


class ColorServerEmbedder(TextEmbedder, ImageBytesEmbedder):
    """Embeds search queries. Runs on the server."""

    def embedding_space_spec(self) -> ls.EmbeddingSpaceSpec:
        """Describe the shared mean-color space."""
        return ls.EmbeddingSpaceSpec(space_key=SPACE_KEY, dimension=EMBEDDING_DIMENSION)

    def embed_text(self, texts: list[str]) -> ls.EmbeddingResult:
        """Embed each color name, and skip text that names no known color."""
        return _result(rows=[COLOR_VECTORS.get(text.strip().lower()) for text in texts])

    def embed_image_bytes(self, images: list[bytes]) -> ls.EmbeddingResult:
        """Embed each uploaded image as its mean color."""
        return _result(rows=[_mean_color(image=Image.open(io.BytesIO(data))) for data in images])


def main() -> None:
    """Start the server, create the dataset and start the GUI."""
    env = Env()
    env.read_env()
    api_key = secrets.token_urlsafe()

    # Part 1: start the server.
    server = multiprocessing.Process(target=_serve, kwargs={"api_key": api_key}, daemon=True)
    server.start()
    _wait_for_server(api_key=api_key)

    # Part 2: fill the embedding space at ingestion, then point it at the server.
    db_manager.connect(cleanup_existing=True)
    ls.register_default_embedder(embedder=ColorPathEmbedder())
    dataset = ls.ImageDataset.create()
    dataset.add_images_from_path(path=env.path("EXAMPLES_DATASET_PATH"))
    ls.register_remote_embedder(dataset=dataset, url=SERVER_URL, api_key=api_key)

    ls.start_gui()


def _serve(api_key: str) -> None:
    lightly_studio_serve.serve(embedder=ColorServerEmbedder(), port=SERVER_PORT, api_key=api_key)


def _wait_for_server(api_key: str) -> None:
    deadline = time.monotonic() + SERVER_STARTUP_TIMEOUT_SECONDS
    while time.monotonic() < deadline:
        try:
            httpx.get(
                f"{SERVER_URL}{protocol.DESCRIBE_PATH}",
                headers={"Authorization": f"Bearer {api_key}"},
            ).raise_for_status()
            return
        except httpx.HTTPError:
            time.sleep(0.2)
    raise RuntimeError(f"The embedding server at {SERVER_URL} did not start.")


def _mean_color(image: Image.Image) -> list[float]:
    pixels = np.asarray(image.convert("RGB"), dtype=np.float32) / 255.0
    return [float(value) for value in pixels.mean(axis=(0, 1))]


def _result(rows: list[list[float] | None]) -> ls.EmbeddingResult:
    kept_indices = [index for index, row in enumerate(rows) if row is not None]
    embeddings: NDArray[np.float32] = np.array(
        [rows[index] for index in kept_indices], dtype=np.float32
    ).reshape(len(kept_indices), EMBEDDING_DIMENSION)
    return ls.EmbeddingResult(embeddings=embeddings, kept_indices=kept_indices)


# The guard keeps the server subprocess from running `main` again on import.
if __name__ == "__main__":
    main()
