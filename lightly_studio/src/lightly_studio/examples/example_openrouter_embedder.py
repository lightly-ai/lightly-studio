"""Example of how to use an embedding model from OpenRouter.

OpenRouter serves many embedding models behind one HTTP API. This example uses Google
Gemini Embedding 2, which embeds text and images into one shared space. Thus text
search, image search and the embedding plot all work without a local GPU.

The embedder below subclasses one interface per input it can embed: images by path,
uploaded images as bytes, annotation crops and text.

Set these environment variables, for example in a ``.env`` file:

- ``OPENROUTER_API_KEY``: Your OpenRouter API key.
- ``EXAMPLES_DATASET_PATH``: A folder with images.

The images and text queries go to OpenRouter and to the model provider. Do not use this
example with data that must stay on your machine.
"""

from __future__ import annotations

import base64
import io
import time
from collections.abc import Sequence
from typing import Any, Callable, TypeVar, Union

import fsspec
import httpx
import numpy as np
from environs import Env
from lightly_studio_serve.embedder import (
    ImageBytesEmbedder,
    ImageCropPathEmbedder,
    ImagePathEmbedder,
    TextEmbedder,
)
from numpy.typing import NDArray
from PIL import Image
from tqdm import tqdm

import lightly_studio as ls
from lightly_studio.core.file_outcome_report import BROKEN_IMAGE_ERRORS
from lightly_studio.database import db_manager

OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
MODEL = "google/gemini-embedding-2"
EMBEDDING_DIMENSION = 768
MAX_ATTEMPTS = 5

_Item = TypeVar("_Item")
_EmbeddingInput = Union[str, dict[str, Any]]


class OpenRouterEmbedder(
    ImagePathEmbedder,
    ImageBytesEmbedder,
    ImageCropPathEmbedder,
    TextEmbedder,
):
    """Embeds images and text with a multimodal embedding model on OpenRouter.

    Each embed method sends its inputs in batches to the OpenRouter embeddings endpoint.
    Images are made smaller and sent as base64 JPEG data. An image that cannot be read is
    skipped and is not in ``kept_indices``.
    """

    def __init__(
        self,
        api_key: str,
        model: str = MODEL,
        dimension: int = EMBEDDING_DIMENSION,
        batch_size: int = 16,
        max_image_side: int = 1024,
    ) -> None:
        """Create the HTTP client.

        Args:
            api_key: The OpenRouter API key.
            model: The OpenRouter model ID. The model must embed images and text.
            dimension: The length of each embedding. The model must support it.
            batch_size: The number of inputs in one request.
            max_image_side: The maximum width and height in pixels of a sent image.
        """
        self._model = model
        self._dimension = dimension
        self._batch_size = batch_size
        self._max_image_side = max_image_side
        # An httpx.Client is thread-safe, so the GUI can call the embedder from more
        # than one thread.
        self._client = httpx.Client(
            base_url=OPENROUTER_BASE_URL,
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=httpx.Timeout(60.0),
        )

    def embedding_space_spec(self) -> ls.EmbeddingSpaceSpec:
        """Describe the embedding space.

        The model and the dimension are part of the key. Embeddings with a different
        model or dimension are not comparable, so they get a different space.
        """
        return ls.EmbeddingSpaceSpec(
            space_key=f"openrouter/{self._model}@{self._dimension}",
            dimension=self._dimension,
        )

    def embed_images(self, paths: list[str]) -> ls.EmbeddingResult:
        """Embed images given by path (used at ingestion)."""
        return self._embed_items(
            items=paths,
            to_input=lambda path: self._image_input(image=_read_image(path=path)),
            show_progress=True,
        )

    def embed_image_bytes(self, images: list[bytes]) -> ls.EmbeddingResult:
        """Embed uploaded images given as encoded bytes (for image search in the GUI)."""
        return self._embed_items(
            items=images,
            to_input=lambda data: self._image_input(image=_decode_image(data=data)),
            show_progress=False,
        )

    def embed_image_crops(self, crops: list[ls.ImageCrop]) -> ls.EmbeddingResult:
        """Embed annotation crops given by image path and pixel box (used at ingestion)."""
        return self._embed_items(
            items=crops,
            to_input=lambda crop: self._image_input(image=_read_crop(crop=crop)),
            show_progress=True,
        )

    def embed_text(self, texts: list[str]) -> ls.EmbeddingResult:
        """Embed text queries into the same space as the images (for text search)."""
        return self._embed_items(items=texts, to_input=lambda text: text, show_progress=False)

    def _embed_items(
        self,
        items: Sequence[_Item],
        to_input: Callable[[_Item], _EmbeddingInput | None],
        show_progress: bool,
    ) -> ls.EmbeddingResult:
        """Convert the items to request inputs batch by batch, and embed each batch.

        Items are converted one batch at a time, so only one batch of encoded images
        is in memory. An item that converts to ``None`` is skipped.
        """
        rows: list[NDArray[np.float32]] = []
        kept_indices: list[int] = []
        with tqdm(
            total=len(items),
            desc="Embedding with OpenRouter",
            unit=" inputs",
            disable=not show_progress,
        ) as progress_bar:
            for start in range(0, len(items), self._batch_size):
                batch_inputs: list[_EmbeddingInput] = []
                for index in range(start, min(start + self._batch_size, len(items))):
                    embedding_input = to_input(items[index])
                    if embedding_input is None:
                        continue
                    batch_inputs.append(embedding_input)
                    kept_indices.append(index)
                if batch_inputs:
                    rows.append(self._request_embeddings(inputs=batch_inputs))
                progress_bar.update(min(self._batch_size, len(items) - start))

        embeddings = (
            np.concatenate(rows) if rows else np.empty((0, self._dimension), dtype=np.float32)
        )
        return ls.EmbeddingResult(embeddings=embeddings, kept_indices=kept_indices)

    def _request_embeddings(self, inputs: list[_EmbeddingInput]) -> NDArray[np.float32]:
        """Send one batch to OpenRouter and return the embeddings in input order.

        N is the number of inputs and D is the embedding dimension.

        Returns:
            The embeddings of shape (N, D).

        Raises:
            RuntimeError: If OpenRouter returns an error or an unexpected shape.
        """
        body = self._post_with_retry(
            payload={
                "model": self._model,
                "input": inputs,
                "dimensions": self._dimension,
            }
        )
        if "error" in body:
            raise RuntimeError(f"OpenRouter returned an error: {body['error']}")

        data = sorted(body["data"], key=lambda item: item["index"])
        embeddings = np.asarray([item["embedding"] for item in data], dtype=np.float32)
        expected_shape = (len(inputs), self._dimension)
        if embeddings.shape != expected_shape:
            raise RuntimeError(
                f"OpenRouter returned embeddings of shape {embeddings.shape}, "
                f"expected {expected_shape}."
            )
        return embeddings

    def _post_with_retry(self, payload: dict[str, Any]) -> dict[str, Any]:
        """POST a payload to the embeddings endpoint and return the JSON body.

        Hosted APIs can fail for a short time: HTTP 429 (rate limit) or 5xx (provider
        problem). Ingestion sends many batches, so one such failure must not stop it.

        Raises:
            httpx.HTTPStatusError: If the request still fails after all retries, or
                fails with an error that a retry cannot fix.
        """
        for attempt in range(1, MAX_ATTEMPTS + 1):
            try:
                response = self._client.post("/embeddings", json=payload)
            except httpx.TransportError:
                # A connection reset or a timeout is usually temporary.
                if attempt == MAX_ATTEMPTS:
                    raise
                time.sleep(_backoff_seconds(attempt=attempt))
                continue

            if attempt == MAX_ATTEMPTS or not _is_temporary_failure(response=response):
                response.raise_for_status()
                body: dict[str, Any] = response.json()
                return body
            time.sleep(_retry_after_seconds(response=response, attempt=attempt))
        raise AssertionError("The last attempt returns or raises.")

    def _image_input(self, image: Image.Image | None) -> dict[str, Any] | None:
        """Convert an image to an OpenRouter image input, or ``None`` if it is missing."""
        if image is None:
            return None
        return _to_image_input(image=image, max_side=self._max_image_side)


def _read_image(path: str) -> Image.Image | None:
    try:
        with fsspec.open(path, "rb") as file, Image.open(file) as opened_image:
            image: Image.Image = opened_image.convert("RGB")
    except BROKEN_IMAGE_ERRORS:
        return None
    return image


def _read_crop(crop: ls.ImageCrop) -> Image.Image | None:
    image = _read_image(path=crop.filepath)
    if image is None:
        return None
    return image.crop((crop.x, crop.y, crop.x + crop.width, crop.y + crop.height))


def _decode_image(data: bytes) -> Image.Image | None:
    try:
        with Image.open(io.BytesIO(data)) as opened_image:
            image: Image.Image = opened_image.convert("RGB")
    except BROKEN_IMAGE_ERRORS:
        return None
    return image


def _is_temporary_failure(response: httpx.Response) -> bool:
    # A 429 is a rate limit and a 5xx is a problem at OpenRouter or the provider. Other
    # errors, such as 401 (bad key) or 402 (no credits), do not go away with a retry.
    return (
        response.status_code == httpx.codes.TOO_MANY_REQUESTS
        or response.status_code >= httpx.codes.INTERNAL_SERVER_ERROR
    )


def _retry_after_seconds(response: httpx.Response, attempt: int) -> float:
    # Use the wait time that the server asks for, if it is given in seconds.
    try:
        return float(response.headers["Retry-After"])
    except (KeyError, ValueError):
        return _backoff_seconds(attempt=attempt)


def _backoff_seconds(attempt: int) -> float:
    # Wait 1, 2, 4, 8 seconds after attempt 1, 2, 3, 4.
    return float(2 ** (attempt - 1))


def _to_image_input(image: Image.Image, max_side: int) -> dict[str, Any]:
    # A smaller image makes the request faster. The model resizes large images anyway.
    image.thumbnail((max_side, max_side))
    buffer = io.BytesIO()
    image.save(buffer, format="JPEG", quality=90)
    encoded = base64.b64encode(buffer.getvalue()).decode("ascii")
    return {
        "content": [
            {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{encoded}"}}
        ]
    }


# Read environment variables
env = Env()
env.read_env()

# Cleanup an existing database
db_manager.connect(cleanup_existing=True)

# Register the OpenRouter embedder BEFORE creating the dataset. It becomes the default
# for every capability it implements, so ingestion and the GUI use it.
ls.register_default_embedder(embedder=OpenRouterEmbedder(api_key=env.str("OPENROUTER_API_KEY")))

# Create a Dataset from a path. Images are embedded on OpenRouter.
dataset = ls.ImageDataset.create()
dataset.add_images_from_path(path=str(env.path("EXAMPLES_DATASET_PATH")))

ls.start_gui()
