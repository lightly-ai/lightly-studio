"""Example of an import and search through an embedder on a remote server.

A subprocess serves ``ColorServerEmbedder`` with ``lightly_studio_serve.serve``.
``ls.register_default_embedder`` registers the server before the import, so the import embeds
the images on the server and the dataset stores the URL and the API key. Search then embeds
the queries on the same server. The embedder maps an image to its mean color, so no model is
downloaded. Search for "red", "green", "blue" or "white", or paste an image.
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
from lightly_studio_serve.embedder import ImageBytesEmbedder, TextEmbedder
from PIL import Image

import lightly_studio as ls
from lightly_studio.database import db_manager
from lightly_studio.embed.remote import connection
from lightly_studio.embed.remote.embedder import RemoteEmbedder

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


class ColorServerEmbedder(TextEmbedder, ImageBytesEmbedder):
    """Embeds the images at import and the search queries. Runs on the server."""

    def embedding_space_spec(self) -> ls.EmbeddingSpaceSpec:
        """Describe the mean-color space."""
        return ls.EmbeddingSpaceSpec(space_key=SPACE_KEY, dimension=EMBEDDING_DIMENSION)

    def embed_text(self, texts: list[str]) -> ls.EmbeddingResult:
        """Embed each text as the first color it names, or as white."""
        return _result(rows=[_text_color(text=text) for text in texts])

    def embed_image_bytes(self, images: list[bytes]) -> ls.EmbeddingResult:
        """Embed each image as its mean color."""
        return _result(rows=[_mean_color(image=Image.open(io.BytesIO(data))) for data in images])


def main() -> None:
    """Start the server, create the dataset and start the GUI."""
    env = Env()
    env.read_env()
    api_key = secrets.token_urlsafe()

    server = multiprocessing.Process(target=_serve, kwargs={"api_key": api_key}, daemon=True)
    server.start()
    _wait_for_server(server=server, api_key=api_key)

    db_manager.connect(cleanup_existing=True)
    # The registry holds the embedder, and with it the client, until the process ends
    ls.register_default_embedder(
        embedder=RemoteEmbedder.connect(
            client=connection.build_client(url=SERVER_URL), api_key=api_key
        )
    )
    dataset = ls.ImageDataset.create()
    dataset.add_images_from_path(path=env.path("EXAMPLES_DATASET_PATH"))
    ls.start_gui()


def _serve(api_key: str) -> None:
    lightly_studio_serve.serve(embedder=ColorServerEmbedder(), port=SERVER_PORT, api_key=api_key)


def _wait_for_server(server: multiprocessing.Process, api_key: str) -> None:
    deadline = time.monotonic() + SERVER_STARTUP_TIMEOUT_SECONDS
    while time.monotonic() < deadline:
        if not server.is_alive():
            raise RuntimeError(f"The embedding server stopped with exit code {server.exitcode}.")
        try:
            httpx.get(
                url=f"{SERVER_URL}{protocol.DESCRIBE_PATH}",
                headers={"Authorization": f"Bearer {api_key}"},
            ).raise_for_status()
            return
        except httpx.HTTPError:
            time.sleep(0.2)
    raise RuntimeError(f"The embedding server at {SERVER_URL} did not start.")


def _mean_color(image: Image.Image) -> list[float]:
    pixels = np.asarray(image.convert("RGB"), dtype=np.float32) / 255.0
    return [float(value) for value in pixels.mean(axis=(0, 1))]


def _text_color(text: str) -> list[float]:
    colors = [word for word in text.lower().split() if word in COLOR_VECTORS]
    return COLOR_VECTORS[colors[0]] if colors else COLOR_VECTORS["white"]


def _result(rows: list[list[float]]) -> ls.EmbeddingResult:
    embeddings = np.array(rows, dtype=np.float32).reshape(len(rows), EMBEDDING_DIMENSION)
    return ls.EmbeddingResult(embeddings=embeddings, kept_indices=list(range(len(rows))))


# The guard keeps the server subprocess from running `main` again on import.
if __name__ == "__main__":
    main()
