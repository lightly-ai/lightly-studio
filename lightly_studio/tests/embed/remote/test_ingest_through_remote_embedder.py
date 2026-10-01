"""Import a dataset through `register_default_embedder` with a real embedding server.

A restart is a new embedder registry. After it, only the dataset can name the server.
"""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path
from uuid import UUID

import numpy as np
import pytest
from lightly_studio_serve.embedder import Capability, ImageBytesEmbedder, TextEmbedder
from lightly_studio_serve.types import EmbeddingResult, EmbeddingSpaceSpec
from pytest_mock import MockerFixture

import lightly_studio
from lightly_studio import ImageDataset
from lightly_studio.core.annotation import CreateObjectDetection
from lightly_studio.embed import embed_samples, embedder_registry
from lightly_studio.embed.embedder_registry import EmbedderRegistry
from lightly_studio.embed.random_embedder import RandomEmbedder
from lightly_studio.embed.remote import connection
from lightly_studio.embed.remote.embedder import RemoteEmbedder
from lightly_studio.models.collection import SampleType
from lightly_studio.models.embedding_model import EmbeddingModelTable
from lightly_studio.resolvers import (
    collection_embedding_model_resolver,
    collection_resolver,
    sample_embedding_resolver,
)
from tests.embed.remote import color_embedder, threaded_server
from tests.embed.remote.color_embedder import ColorQueryEmbedder

_API_KEY = "test-api-key"

# The fixture gives each test its own embedder registry and the test database.
pytestmark = pytest.mark.usefixtures("patch_collection")

# Another dimension than the one of the color space that the dataset stores
_OTHER_DIMENSION = color_embedder.DIMENSION + 1


class _OtherDimensionColorEmbedder(TextEmbedder, ImageBytesEmbedder):
    """Produces the color space with another dimension."""

    def embedding_space_spec(self) -> EmbeddingSpaceSpec:
        return EmbeddingSpaceSpec(space_key=color_embedder.SPACE_KEY, dimension=_OTHER_DIMENSION)

    def embed_text(self, texts: list[str]) -> EmbeddingResult:
        return _zeros(count=len(texts))

    def embed_image_bytes(self, images: list[bytes]) -> EmbeddingResult:
        return _zeros(count=len(images))


@pytest.fixture
def query_embedder() -> ColorQueryEmbedder:
    return ColorQueryEmbedder()


@pytest.fixture
def server_url(query_embedder: ColorQueryEmbedder) -> Iterator[str]:
    with threaded_server.serve(embedder=query_embedder, api_key=_API_KEY) as url:
        yield url


@pytest.fixture
def dataset(server_url: str, tmp_path: Path) -> Iterator[ImageDataset]:
    """A dataset that the server embedded at the import, with one registration only."""
    images = tmp_path / "images"
    images.mkdir()
    color_embedder.write_color_images(directory=images)
    with connection.build_client(url=server_url) as client:
        lightly_studio.register_default_embedder(
            embedder=RemoteEmbedder.connect(client=client, api_key=_API_KEY)
        )
        dataset = ImageDataset.create(name="colors")
        dataset.add_images_from_path(path=images)
        yield dataset


def test_add_images_from_path__stores_the_server(dataset: ImageDataset, server_url: str) -> None:
    default_model = collection_embedding_model_resolver.get_default_model_by_collection_id(
        session=dataset.session, collection_id=dataset.collection_id
    )

    assert default_model is not None
    assert default_model.name == color_embedder.SPACE_KEY
    assert default_model.remote_embedder_url == server_url
    assert default_model.api_key == _API_KEY
    embedding_count = sample_embedding_resolver.get_embedding_count(
        session=dataset.session,
        collection_id=dataset.collection_id,
        embedding_model_id=default_model.embedding_model_id,
    )
    assert embedding_count == 3


def test_embed_annotation_collection__uses_the_server_space(
    dataset: ImageDataset, server_url: str
) -> None:
    annotation_collection_id = _add_box_to_each_image(dataset=dataset)

    embed_samples.embed_annotation_collection(
        session=dataset.session, annotation_collection_id=annotation_collection_id
    )

    # The crops use the model row of the images, which stores the server
    crop_model = _default_model(dataset=dataset, collection_id=annotation_collection_id)
    image_model = _default_model(dataset=dataset, collection_id=dataset.collection_id)
    assert crop_model.embedding_model_id == image_model.embedding_model_id
    assert crop_model.remote_embedder_url == server_url
    embedding_count = sample_embedding_resolver.get_embedding_count(
        session=dataset.session,
        collection_id=annotation_collection_id,
        embedding_model_id=crop_model.embedding_model_id,
    )
    assert embedding_count == 3


def test_embed_annotation_collection__after_restart(
    dataset: ImageDataset, query_embedder: ColorQueryEmbedder, mocker: MockerFixture
) -> None:
    annotation_collection_id = _add_box_to_each_image(dataset=dataset)
    embed_samples.embed_annotation_collection(
        session=dataset.session, annotation_collection_id=annotation_collection_id
    )
    mocker.patch.object(embedder_registry, "get_registry", return_value=EmbedderRegistry())
    _add_box_to_each_image(dataset=dataset)
    call_count = query_embedder.call_count

    embed_samples.embed_annotation_collection(
        session=dataset.session, annotation_collection_id=annotation_collection_id
    )

    # The 3 new crops fit in one request to the stored server
    assert query_embedder.call_count == call_count + 1
    crop_model = _default_model(dataset=dataset, collection_id=annotation_collection_id)
    embedding_count = sample_embedding_resolver.get_embedding_count(
        session=dataset.session,
        collection_id=annotation_collection_id,
        embedding_model_id=crop_model.embedding_model_id,
    )
    assert embedding_count == 6


def test_embed_annotation_collection__new_collection_after_restart(
    dataset: ImageDataset, server_url: str, mocker: MockerFixture
) -> None:
    mocker.patch.object(embedder_registry, "get_registry", return_value=EmbedderRegistry())
    annotation_collection_id = _add_box_to_each_image(dataset=dataset)

    embed_samples.embed_annotation_collection(
        session=dataset.session, annotation_collection_id=annotation_collection_id
    )

    # Nothing is registered, so the new crops take the model row of the images
    crop_model = _default_model(dataset=dataset, collection_id=annotation_collection_id)
    image_model = _default_model(dataset=dataset, collection_id=dataset.collection_id)
    assert crop_model.embedding_model_id == image_model.embedding_model_id
    assert crop_model.remote_embedder_url == server_url
    embedding_count = sample_embedding_resolver.get_embedding_count(
        session=dataset.session,
        collection_id=annotation_collection_id,
        embedding_model_id=crop_model.embedding_model_id,
    )
    assert embedding_count == 3


def test_embed_annotation_collection__new_collection_after_restart_with_registration(
    dataset: ImageDataset, mocker: MockerFixture
) -> None:
    registry = EmbedderRegistry()
    registry.register(
        embedder=RandomEmbedder(dimension=4), bootstrap_for={Capability.IMAGE_CROP_PATH}
    )
    mocker.patch.object(embedder_registry, "get_registry", return_value=registry)
    annotation_collection_id = _add_box_to_each_image(dataset=dataset)

    embed_samples.embed_annotation_collection(
        session=dataset.session, annotation_collection_id=annotation_collection_id
    )

    # The registered crop embedder wins over the server of the images
    crop_model = _default_model(dataset=dataset, collection_id=annotation_collection_id)
    assert crop_model.name == "random_model"
    assert crop_model.embedding_dimension == 4
    assert crop_model.remote_embedder_url is None


def test_text_search__after_restart(
    dataset: ImageDataset, query_embedder: ColorQueryEmbedder, mocker: MockerFixture
) -> None:
    call_count = query_embedder.call_count
    mocker.patch.object(embedder_registry, "get_registry", return_value=EmbedderRegistry())

    embedding = embed_samples.embed_text_for_collection(
        session=dataset.session, collection_id=dataset.collection_id, text="red"
    )

    # The server embeds a color name as its one-hot vector.
    assert embedding == [1.0, 0.0, 0.0]
    assert query_embedder.call_count == call_count + 1


def test_add_images_from_path__dimension_mismatch_after_restart(
    dataset: ImageDataset, tmp_path: Path, mocker: MockerFixture
) -> None:
    mocker.patch.object(embedder_registry, "get_registry", return_value=EmbedderRegistry())
    more_images = tmp_path / "more"
    more_images.mkdir()
    color_embedder.write_color_images(directory=more_images)

    with (
        threaded_server.serve(embedder=_OtherDimensionColorEmbedder(), api_key=_API_KEY) as url,
        connection.build_client(url=url) as client,
    ):
        lightly_studio.register_default_embedder(
            embedder=RemoteEmbedder.connect(client=client, api_key=_API_KEY)
        )
        with pytest.raises(ValueError, match=r"does not match"):
            dataset.add_images_from_path(path=more_images)
    # The new images are stored without an embedding
    assert len(list(dataset)) == 6
    assert _embedding_count(dataset=dataset) == 3

    # After a restart without the other server, the stored server embeds them
    mocker.patch.object(embedder_registry, "get_registry", return_value=EmbedderRegistry())
    dataset.add_images_from_path(path=more_images)

    assert _embedding_count(dataset=dataset) == 6


def _zeros(count: int) -> EmbeddingResult:
    return EmbeddingResult(
        embeddings=np.zeros((count, _OTHER_DIMENSION), dtype=np.float32),
        kept_indices=list(range(count)),
    )


def _embedding_count(dataset: ImageDataset) -> int:
    default_model = collection_embedding_model_resolver.get_default_model_by_collection_id(
        session=dataset.session, collection_id=dataset.collection_id
    )
    assert default_model is not None
    return sample_embedding_resolver.get_embedding_count(
        session=dataset.session,
        collection_id=dataset.collection_id,
        embedding_model_id=default_model.embedding_model_id,
    )


def _add_box_to_each_image(dataset: ImageDataset) -> UUID:
    """Add one box to each 8x8 image and return the id of the annotation collection."""
    for sample in dataset:
        sample.add_annotation(
            annotation=CreateObjectDetection(class_name="box", x=0, y=0, width=4, height=4)
        )
    return collection_resolver.get_or_create_child_collection(
        session=dataset.session,
        collection_id=dataset.collection_id,
        sample_type=SampleType.ANNOTATION,
    )


def _default_model(dataset: ImageDataset, collection_id: UUID) -> EmbeddingModelTable:
    default_model = collection_embedding_model_resolver.get_default_model_by_collection_id(
        session=dataset.session, collection_id=collection_id
    )
    assert default_model is not None
    return default_model
