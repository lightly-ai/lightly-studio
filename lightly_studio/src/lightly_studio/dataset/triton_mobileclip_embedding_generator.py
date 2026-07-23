"""Triton-backed path-based embedding generator."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any
from uuid import UUID

import numpy as np
import tritonclient.grpc as grpcclient  # type: ignore[import-untyped]
import xxhash
from numpy.typing import NDArray
from tqdm import tqdm

from lightly_studio.models.embedding_model import EmbeddingModelCreate

from .embedding_generator import ImageCrop, ImageEmbeddingGenerator
from .image_embedding import ImageEmbeddingResult

# Maximum number of inputs sent in one Triton inference request.
DEFAULT_REQUEST_BATCH_SIZE = 512


class _TritonNames:
    """Names in the Triton model interface."""

    IMAGE_PATH = "IMAGE_PATH"
    TEXT = "TEXT"
    CROP_X = "CROP_X"
    CROP_Y = "CROP_Y"
    CROP_WIDTH = "CROP_WIDTH"
    CROP_HEIGHT = "CROP_HEIGHT"
    EMBEDDING = "EMBEDDING"


class TritonEmbeddingGenerator(ImageEmbeddingGenerator):
    """Embedding model served by a compatible Triton gRPC endpoint.

    The endpoint must accept ``TEXT`` or ``IMAGE_PATH`` inputs, optionally accept
    crop-coordinate inputs, and return an ``EMBEDDING`` output.
    """

    def __init__(self, url: str, model_name: str) -> None:
        """Initialize the Triton client and read the embedding output dimension."""
        self._url = url
        self._model_name = model_name
        self._client = grpcclient.InferenceServerClient(url=url)
        metadata = self._client.get_model_metadata(model_name=model_name)
        self._embedding_dimension = _get_embedding_dimension(metadata=metadata)
        self._model_hash = _get_model_hash(url=url, model_name=model_name)

    def get_embedding_model_input(self, collection_id: UUID) -> EmbeddingModelCreate:
        """Build the database representation of this embedding model."""
        return EmbeddingModelCreate(
            name=self._model_name,
            embedding_model_hash=self._model_hash,
            embedding_dimension=self._embedding_dimension,
            collection_id=collection_id,
        )

    def embed_text(self, text: str) -> list[float]:
        """Embed a text query."""
        embeddings = self._infer_embeddings(
            inputs=[_bytes_input(name=_TritonNames.TEXT, values=[text])], expected_count=1
        )
        result: list[float] = embeddings[0].tolist()
        return result

    def embed_images(
        self, filepaths: list[str], show_progress: bool = True
    ) -> ImageEmbeddingResult:
        """Embed image paths, forwarding remote URLs unchanged to Triton."""
        embeddings = self._embed_in_chunks(
            values=filepaths,
            make_inputs=lambda paths: [_bytes_input(name=_TritonNames.IMAGE_PATH, values=paths)],
            show_progress=show_progress,
            progress_description="Generating embeddings",
            progress_unit=" images",
        )
        return ImageEmbeddingResult(
            embeddings=embeddings,
            kept_indices=list(range(len(filepaths))),
        )

    def embed_image_crops(
        self, image_crops: list[ImageCrop], show_progress: bool = True
    ) -> NDArray[np.float32]:
        """Embed image crops represented by their source paths and coordinates."""
        return self._embed_in_chunks(
            values=image_crops,
            make_inputs=_crop_inputs,
            show_progress=show_progress,
            progress_description="Generating crop embeddings",
            progress_unit=" crops",
        )

    def _embed_in_chunks(
        self,
        values: Sequence[str] | Sequence[ImageCrop],
        make_inputs: Any,
        show_progress: bool,
        progress_description: str,
        progress_unit: str,
    ) -> NDArray[np.float32]:
        if not values:
            return np.empty((0, self._embedding_dimension), dtype=np.float32)

        chunks = []
        with tqdm(
            total=len(values),
            desc=progress_description,
            unit=progress_unit,
            disable=not show_progress,
        ) as progress_bar:
            for index in range(0, len(values), DEFAULT_REQUEST_BATCH_SIZE):
                chunk = values[index : index + DEFAULT_REQUEST_BATCH_SIZE]
                chunks.append(
                    self._infer_embeddings(
                        inputs=make_inputs(chunk),
                        expected_count=len(chunk),
                    )
                )
                progress_bar.update(len(chunk))
        return np.concatenate(chunks, axis=0)

    def _infer_embeddings(
        self, inputs: list[grpcclient.InferInput], expected_count: int
    ) -> NDArray[np.float32]:
        result = self._client.infer(
            model_name=self._model_name,
            inputs=inputs,
            outputs=[grpcclient.InferRequestedOutput(_TritonNames.EMBEDDING)],
        )
        output = result.as_numpy(_TritonNames.EMBEDDING)
        if output is None:
            raise ValueError(f"Triton response is missing output '{_TritonNames.EMBEDDING}'.")

        embeddings = np.asarray(output, dtype=np.float32)
        expected_shape = (expected_count, self._embedding_dimension)
        if embeddings.shape != expected_shape:
            raise ValueError(
                "Triton response has invalid embedding shape "
                f"{embeddings.shape}; expected {expected_shape}."
            )
        return embeddings


def _bytes_input(name: str, values: Sequence[str]) -> grpcclient.InferInput:
    encoded_values = [value.encode("utf-8") for value in values]
    infer_input = grpcclient.InferInput(name, [len(encoded_values)], "BYTES")
    infer_input.set_data_from_numpy(np.asarray(encoded_values, dtype=object))
    return infer_input


def _crop_inputs(image_crops: Sequence[ImageCrop]) -> list[grpcclient.InferInput]:
    return [
        _bytes_input(name=_TritonNames.IMAGE_PATH, values=[crop.filepath for crop in image_crops]),
        _int64_input(name=_TritonNames.CROP_X, values=[crop.x for crop in image_crops]),
        _int64_input(name=_TritonNames.CROP_Y, values=[crop.y for crop in image_crops]),
        _int64_input(name=_TritonNames.CROP_WIDTH, values=[crop.width for crop in image_crops]),
        _int64_input(name=_TritonNames.CROP_HEIGHT, values=[crop.height for crop in image_crops]),
    ]


def _int64_input(name: str, values: Sequence[int]) -> grpcclient.InferInput:
    infer_input = grpcclient.InferInput(name, [len(values)], "INT64")
    infer_input.set_data_from_numpy(np.asarray(values, dtype=np.int64))
    return infer_input


def _get_embedding_dimension(metadata: Any) -> int:
    outputs = metadata["outputs"] if isinstance(metadata, dict) else metadata.outputs
    for output in outputs:
        name = output["name"] if isinstance(output, dict) else output.name
        if name != _TritonNames.EMBEDDING:
            continue
        shape = output["shape"] if isinstance(output, dict) else output.shape
        if shape[-1] <= 0:
            raise ValueError(f"Triton output '{_TritonNames.EMBEDDING}' has invalid shape {shape}.")
        return int(shape[-1])
    raise ValueError(f"Triton model does not expose output '{_TritonNames.EMBEDDING}'.")


def _get_model_hash(url: str, model_name: str) -> str:
    hasher = xxhash.xxh64()
    hasher.update(f"triton-grpc:{url}:{model_name}")
    return hasher.hexdigest()
