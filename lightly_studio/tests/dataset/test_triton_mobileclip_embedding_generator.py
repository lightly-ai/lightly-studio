from __future__ import annotations

from typing import Any
from uuid import uuid4

import numpy as np
import pytest
from numpy.typing import NDArray

pytest.importorskip("tritonclient.grpc")

from lightly_studio.dataset.embedding_generator import ImageCrop
from lightly_studio.dataset.triton_mobileclip_embedding_generator import (
    DEFAULT_REQUEST_BATCH_SIZE,
    TritonEmbeddingGenerator,
)

EMBEDDING_DIMENSION = 3


class FakeTritonResult:
    def __init__(self, output: NDArray[np.float32] | None) -> None:
        self.output = output

    def as_numpy(self, name: str) -> NDArray[np.float32] | None:
        assert name == "EMBEDDING"
        return self.output


class FakeTritonClient:
    def __init__(self, url: str) -> None:
        self.url = url
        self.calls: list[dict[str, Any]] = []

    def get_model_metadata(self, model_name: str) -> dict[str, Any]:
        return {"name": model_name, "outputs": [{"name": "EMBEDDING", "shape": [-1, 3]}]}

    def infer(self, model_name: str, inputs: list[Any], outputs: list[Any]) -> FakeTritonResult:
        self.calls.append({"model_name": model_name, "inputs": inputs, "outputs": outputs})
        batch_size = int(inputs[0]._get_tensor().shape[0])
        return FakeTritonResult(np.ones((batch_size, EMBEDDING_DIMENSION), dtype=np.float32))


@pytest.fixture
def generator(monkeypatch: pytest.MonkeyPatch) -> tuple[TritonEmbeddingGenerator, FakeTritonClient]:
    created_client: FakeTritonClient | None = None

    def create_client(url: str) -> FakeTritonClient:
        nonlocal created_client
        created_client = FakeTritonClient(url=url)
        return created_client

    monkeypatch.setattr(
        "lightly_studio.dataset.triton_mobileclip_embedding_generator.grpcclient"
        ".InferenceServerClient",
        create_client,
    )
    embedding_generator = TritonEmbeddingGenerator(url="localhost:8001", model_name="custom-model")
    assert created_client is not None
    return embedding_generator, created_client


def test_get_embedding_model_input(
    generator: tuple[TritonEmbeddingGenerator, FakeTritonClient],
) -> None:
    embedding_generator, _ = generator

    model_input = embedding_generator.get_embedding_model_input(collection_id=uuid4())

    assert model_input.name == "custom-model"
    assert model_input.embedding_dimension == EMBEDDING_DIMENSION


def test_embed_images__forwards_remote_paths_unchanged(
    generator: tuple[TritonEmbeddingGenerator, FakeTritonClient],
) -> None:
    embedding_generator, client = generator

    result = embedding_generator.embed_images(filepaths=["s3://bucket/a.jpg", "gs://bucket/b.jpg"])

    assert result.embeddings.shape == (2, EMBEDDING_DIMENSION)
    assert result.kept_indices == [0, 1]
    input_tensor = client.calls[-1]["inputs"][0]
    assert input_tensor.name() == "IMAGE_PATH"
    assert input_tensor._get_tensor().shape == [2]
    assert b"s3://bucket/a.jpg" in input_tensor._raw_content
    assert b"gs://bucket/b.jpg" in input_tensor._raw_content


def test_embed_images__splits_requests_and_preserves_order(
    generator: tuple[TritonEmbeddingGenerator, FakeTritonClient],
) -> None:
    embedding_generator, client = generator
    filepaths = [f"/data/{index}.jpg" for index in range(DEFAULT_REQUEST_BATCH_SIZE + 1)]

    result = embedding_generator.embed_images(filepaths=filepaths)

    assert result.embeddings.shape == (len(filepaths), EMBEDDING_DIMENSION)
    assert result.kept_indices == list(range(len(filepaths)))
    assert [call["inputs"][0]._get_tensor().shape for call in client.calls] == [[512], [1]]


def test_embed_text__sends_text(
    generator: tuple[TritonEmbeddingGenerator, FakeTritonClient],
) -> None:
    embedding_generator, client = generator

    embedding = embedding_generator.embed_text(text="a cat")

    assert len(embedding) == EMBEDDING_DIMENSION
    assert client.calls[-1]["inputs"][0].name() == "TEXT"


def test_embed_image_crops__sends_paths_and_crop_coordinates(
    generator: tuple[TritonEmbeddingGenerator, FakeTritonClient],
) -> None:
    embedding_generator, client = generator
    image_crops = [ImageCrop(filepath="/data/a.jpg", x=1, y=2, width=3, height=4)]

    embeddings = embedding_generator.embed_image_crops(image_crops=image_crops)

    assert embeddings.shape == (1, EMBEDDING_DIMENSION)
    assert [tensor.name() for tensor in client.calls[-1]["inputs"]] == [
        "IMAGE_PATH",
        "CROP_X",
        "CROP_Y",
        "CROP_WIDTH",
        "CROP_HEIGHT",
    ]


def test_embed_images__invalid_shape_raises(
    generator: tuple[TritonEmbeddingGenerator, FakeTritonClient],
) -> None:
    embedding_generator, client = generator
    client.infer = lambda **_: FakeTritonResult(  # type: ignore[method-assign]
        np.ones((1, EMBEDDING_DIMENSION + 1), dtype=np.float32)
    )

    with pytest.raises(ValueError, match="invalid embedding shape"):
        embedding_generator.embed_images(filepaths=["/data/a.jpg"])


def test_init__invalid_metadata_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    class InvalidMetadataClient(FakeTritonClient):
        def get_model_metadata(self, model_name: str) -> dict[str, Any]:
            return {"name": model_name, "outputs": []}

    monkeypatch.setattr(
        "lightly_studio.dataset.triton_mobileclip_embedding_generator.grpcclient"
        ".InferenceServerClient",
        InvalidMetadataClient,
    )

    with pytest.raises(ValueError, match="does not expose output"):
        TritonEmbeddingGenerator(url="localhost:8001", model_name="custom-model")
