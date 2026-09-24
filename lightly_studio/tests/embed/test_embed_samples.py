"""Tests for the class-free embed_samples interface."""

from __future__ import annotations

import io
import logging
import re
import tempfile
from uuid import UUID, uuid4

import numpy as np
import pytest
from lightly_studio_serve.embedder import (
    ImageBytesEmbedder,
    ImageCropPathEmbedder,
    ImagePathEmbedder,
    ImagePILEmbedder,
    TextEmbedder,
    VideoPathEmbedder,
)
from lightly_studio_serve.types import EmbeddingResult, EmbeddingSpaceSpec, ImageCrop
from PIL import Image
from pytest_mock import MockerFixture
from sqlmodel import Session, select

from lightly_studio.embed import embed_samples, embedder_registry
from lightly_studio.embed.embedder_registry import EmbedderRegistry
from lightly_studio.embed.errors import MissingCapabilityError, RemoteEmbedderUnavailableError
from lightly_studio.embed.random_embedder import RandomEmbedder
from lightly_studio.models.collection import SampleType
from lightly_studio.models.sample_embedding import SampleEmbeddingTable
from lightly_studio.resolvers import (
    collection_embedding_model_resolver,
    collection_resolver,
    sample_embedding_resolver,
)
from tests.helpers_resolvers import (
    ImageStub,
    create_annotation,
    create_annotation_label,
    create_collection,
    create_embedding_model,
    create_image,
    create_images,
)
from tests.resolvers.video.helpers import (
    VideoStub,
    create_video_with_frames,
    create_videos,
)


class _FirstPixelPILEmbedder(ImagePILEmbedder):
    """Embeds each PIL image as its top-left pixel's RGB and drops the last image.

    Deriving the vector from the pixel content, not the input position, makes the test fail
    if ``embed_frame_samples`` matches frames to the wrong sample IDs. A dropped input
    verifies that only kept embeddings are stored. Shares the random model's space so it
    resolves as the collection's default.
    """

    __slots__ = ()

    def embedding_space_spec(self) -> EmbeddingSpaceSpec:
        """Describe the shared random embedding space with dimension 3."""
        return EmbeddingSpaceSpec(space_key="random_model", dimension=3)

    def embed_images_pil(self, images: list[Image.Image]) -> EmbeddingResult:
        """Embed all images but the last as their top-left RGB pixel."""
        kept_indices = list(range(len(images) - 1))
        embeddings = np.array(
            [images[index].getpixel(xy=(0, 0)) for index in kept_indices], dtype=np.float32
        )
        return EmbeddingResult(embeddings=embeddings, kept_indices=kept_indices)


class _PathIndexVideoEmbedder(VideoPathEmbedder):
    """Embeds each video path as the number in its file name and drops the last path.

    Deriving the vector from the path content, not the input position, makes the test fail
    if ``embed_video_samples`` resolves the paths in the wrong order. A dropped input
    verifies that only kept embeddings are stored. Shares the random model's space so it
    resolves as the collection's default.
    """

    __slots__ = ()

    def embedding_space_spec(self) -> EmbeddingSpaceSpec:
        """Describe the shared random embedding space with dimension 2."""
        return EmbeddingSpaceSpec(space_key="random_model", dimension=2)

    def embed_videos(self, paths: list[str]) -> EmbeddingResult:
        """Embed all paths but the last as [number, number], parsed from the file name."""
        kept_indices = list(range(len(paths) - 1))
        embeddings = np.array(
            [[_path_number(path=paths[index])] * 2 for index in kept_indices], dtype=np.float32
        )
        return EmbeddingResult(embeddings=embeddings, kept_indices=kept_indices)


class _BoxXImageCropEmbedder(ImageCropPathEmbedder):
    """Embeds each crop as its left edge x and drops the last crop.

    Deriving the vector from the crop's box, not the input position, makes the test fail
    if ``embed_annotation_collection`` matches crops to the wrong annotation IDs. A dropped
    input verifies that only kept embeddings are stored. Shares the random model's space so
    it resolves as the collection's default.
    """

    __slots__ = ()

    def embedding_space_spec(self) -> EmbeddingSpaceSpec:
        """Describe the shared random embedding space with dimension 3."""
        return EmbeddingSpaceSpec(space_key="random_model", dimension=3)

    def embed_image_crops(self, crops: list[ImageCrop]) -> EmbeddingResult:
        """Embed all crops but the last as [x, x, x], read from the crop's left edge."""
        kept_indices = list(range(len(crops) - 1))
        embeddings = np.array([[crops[index].x] * 3 for index in kept_indices], dtype=np.float32)
        return EmbeddingResult(embeddings=embeddings, kept_indices=kept_indices)


class _PathOnlyEmbedder(ImagePathEmbedder):
    """Embeds each image read from its path as the top-left pixel's RGB.

    Reading the pixel from the file verifies that the upload is written to a readable file.
    Shares the random model's space so it resolves as the collection's default.
    """

    __slots__ = ()

    def embedding_space_spec(self) -> EmbeddingSpaceSpec:
        """Describe the shared random embedding space with dimension 3."""
        return EmbeddingSpaceSpec(space_key="random_model", dimension=3)

    def embed_images(self, paths: list[str]) -> EmbeddingResult:
        """Embed each image at the given path as its top-left RGB pixel."""
        embeddings = np.array(
            [Image.open(path).convert("RGB").getpixel(xy=(0, 0)) for path in paths],
            dtype=np.float32,
        )
        return EmbeddingResult(embeddings=embeddings, kept_indices=list(range(len(paths))))


class _PILOnlyEmbedder(ImagePILEmbedder):
    """Embeds each PIL image as its top-left pixel's RGB.

    Shares the random model's space so it resolves as the collection's default.
    """

    __slots__ = ()

    def embedding_space_spec(self) -> EmbeddingSpaceSpec:
        """Describe the shared random embedding space with dimension 3."""
        return EmbeddingSpaceSpec(space_key="random_model", dimension=3)

    def embed_images_pil(self, images: list[Image.Image]) -> EmbeddingResult:
        """Embed each image as its top-left RGB pixel."""
        embeddings = np.array([image.getpixel(xy=(0, 0)) for image in images], dtype=np.float32)
        return EmbeddingResult(embeddings=embeddings, kept_indices=list(range(len(images))))


class _DropPathEmbedder(ImagePathEmbedder):
    """Drops every path, as a precalculated embedder does for a path it does not know.

    Shares the random model's space so it resolves as the collection's default.
    """

    __slots__ = ()

    def embedding_space_spec(self) -> EmbeddingSpaceSpec:
        """Describe the shared random embedding space with dimension 3."""
        return EmbeddingSpaceSpec(space_key="random_model", dimension=3)

    def embed_images(self, paths: list[str]) -> EmbeddingResult:
        """Drop every path, returning no embedding."""
        del paths
        return EmbeddingResult(embeddings=np.empty((0, 3), dtype=np.float32), kept_indices=[])


class _DropInputEmbedder(ImageBytesEmbedder, TextEmbedder):
    """Drops every input, so image and text queries get an empty result.

    Stands in for an embedder that skips inputs it cannot read. Shares the random model's
    space so it resolves as the collection's default.
    """

    __slots__ = ()

    def embedding_space_spec(self) -> EmbeddingSpaceSpec:
        """Describe the shared random embedding space with dimension 3."""
        return EmbeddingSpaceSpec(space_key="random_model", dimension=3)

    def embed_image_bytes(self, images: list[bytes]) -> EmbeddingResult:
        """Drop every image, returning no embedding."""
        del images
        return EmbeddingResult(embeddings=np.empty((0, 3), dtype=np.float32), kept_indices=[])

    def embed_text(self, texts: list[str]) -> EmbeddingResult:
        """Drop every text, returning no embedding."""
        del texts
        return EmbeddingResult(embeddings=np.empty((0, 3), dtype=np.float32), kept_indices=[])


@pytest.fixture
def patched_registry(mocker: MockerFixture) -> EmbedderRegistry:
    """Route embed_samples to a fresh registry so tests never touch the shared singleton."""
    registry = EmbedderRegistry()
    registry.register(embedder=RandomEmbedder())
    mocker.patch.object(embedder_registry, "get_registry", return_value=registry)
    return registry


@pytest.mark.usefixtures("patched_registry")
def test_embed_image_for_collection(
    db_session: Session,
) -> None:
    """A single image is embedded via the registry with the collection's default model, unstored."""
    collection = create_collection(session=db_session)
    _register_default_random_model(
        session=db_session,
        collection_id=collection.collection_id,
    )

    embedding = embed_samples.embed_image_for_collection(
        session=db_session, collection_id=collection.collection_id, image_bytes=b"image bytes"
    )

    assert len(embedding) == 3
    # Nothing is stored for an interactive query embedding.
    assert _stored_embeddings(session=db_session) == []


@pytest.mark.usefixtures("patched_registry")
def test_embed_image_for_collection__no_default_model(
    db_session: Session,
) -> None:
    """Without a default model the interactive image path raises a clear error."""
    collection = create_collection(session=db_session)
    with pytest.raises(ValueError, match="no default embedding model"):
        embed_samples.embed_image_for_collection(
            session=db_session,
            collection_id=collection.collection_id,
            image_bytes=b"image bytes",
        )


def test_embed_image_for_collection__no_embedder_for_space_raises(
    db_session: Session,
    mocker: MockerFixture,
) -> None:
    """With a default model but no embedder for its space, the query raises."""
    collection = create_collection(session=db_session)
    _register_default_random_model(session=db_session, collection_id=collection.collection_id)
    # An empty registry cannot supply an embedder for the default model's space.
    mocker.patch.object(embedder_registry, "get_registry", return_value=EmbedderRegistry())

    with pytest.raises(MissingCapabilityError, match="cannot embed images"):
        embed_samples.embed_image_for_collection(
            session=db_session,
            collection_id=collection.collection_id,
            image_bytes=b"image bytes",
        )


def test_embed_image_for_collection__no_embedding_raises(
    db_session: Session,
    mocker: MockerFixture,
) -> None:
    """When the embedder drops the image, the query raises instead of an IndexError."""
    collection = create_collection(session=db_session)
    _register_default_random_model(session=db_session, collection_id=collection.collection_id)
    registry = EmbedderRegistry()
    registry.register(embedder=_DropInputEmbedder())
    mocker.patch.object(embedder_registry, "get_registry", return_value=registry)

    with pytest.raises(embed_samples.ImageNotEmbeddedError, match="returned no embedding"):
        embed_samples.embed_image_for_collection(
            session=db_session,
            collection_id=collection.collection_id,
            image_bytes=b"image bytes",
        )


def test_embed_image_for_collection__pil_only_embedder(
    db_session: Session,
    mocker: MockerFixture,
) -> None:
    """An embedder that embeds PIL images only gets the decoded upload."""
    collection = create_collection(session=db_session)
    _register_default_random_model(session=db_session, collection_id=collection.collection_id)
    registry = EmbedderRegistry()
    registry.register(embedder=_PILOnlyEmbedder())
    mocker.patch.object(embedder_registry, "get_registry", return_value=registry)

    embedding = embed_samples.embed_image_for_collection(
        session=db_session,
        collection_id=collection.collection_id,
        image_bytes=_png_bytes(color=(1, 2, 3)),
    )

    assert embedding == [1.0, 2.0, 3.0]


def test_embed_image_for_collection__path_only_embedder(
    db_session: Session,
    mocker: MockerFixture,
) -> None:
    """An embedder that embeds images by path only gets the upload as a temporary file."""
    collection = create_collection(session=db_session)
    _register_default_random_model(session=db_session, collection_id=collection.collection_id)
    registry = EmbedderRegistry()
    registry.register(embedder=_PathOnlyEmbedder())
    mocker.patch.object(embedder_registry, "get_registry", return_value=registry)

    embedding = embed_samples.embed_image_for_collection(
        session=db_session,
        collection_id=collection.collection_id,
        image_bytes=_png_bytes(color=(1, 2, 3)),
    )

    assert embedding == [1.0, 2.0, 3.0]


def test_embed_image_for_collection__path_only_embedder_no_embedding_raises(
    db_session: Session,
    mocker: MockerFixture,
) -> None:
    """A path embedder that returns no embedding does not blame the decoded image."""
    collection = create_collection(session=db_session)
    _register_default_random_model(session=db_session, collection_id=collection.collection_id)
    registry = EmbedderRegistry()
    registry.register(embedder=_DropPathEmbedder())
    mocker.patch.object(embedder_registry, "get_registry", return_value=registry)

    with pytest.raises(embed_samples.ImageNotEmbeddedError, match="cannot embed an upload"):
        embed_samples.embed_image_for_collection(
            session=db_session,
            collection_id=collection.collection_id,
            image_bytes=_png_bytes(),
        )


def test_embed_image_for_collection__path_only_embedder_with_url_raises(
    db_session: Session,
    mocker: MockerFixture,
) -> None:
    """A space with a remote URL skips the path embedder and writes no temporary file."""
    collection = create_collection(session=db_session)
    _register_default_random_model(
        session=db_session, collection_id=collection.collection_id, url="http://embedder.test"
    )
    registry = EmbedderRegistry()
    registry.register(embedder=_PathOnlyEmbedder())
    mocker.patch.object(embedder_registry, "get_registry", return_value=registry)
    spy_temp_dir = mocker.spy(tempfile, "TemporaryDirectory")

    with pytest.raises(RemoteEmbedderUnavailableError):
        embed_samples.embed_image_for_collection(
            session=db_session,
            collection_id=collection.collection_id,
            image_bytes=_png_bytes(),
        )
    spy_temp_dir.assert_not_called()


def test_embed_image_for_collection__pil_only_embedder_with_url(
    db_session: Session,
    mocker: MockerFixture,
) -> None:
    """A PIL embedder next to a text-only remote server still serves image search."""
    collection = create_collection(session=db_session)
    _register_default_random_model(
        session=db_session, collection_id=collection.collection_id, url="http://embedder.test"
    )
    registry = EmbedderRegistry()
    registry.register(embedder=_PILOnlyEmbedder())
    mocker.patch.object(embedder_registry, "get_registry", return_value=registry)

    embedding = embed_samples.embed_image_for_collection(
        session=db_session,
        collection_id=collection.collection_id,
        image_bytes=_png_bytes(color=(1, 2, 3)),
    )

    assert embedding == [1.0, 2.0, 3.0]


def test_embed_image_for_collection__undecodable_bytes_raises(
    db_session: Session,
    mocker: MockerFixture,
) -> None:
    """Bytes that do not decode raise when the embedder has no bytes capability."""
    collection = create_collection(session=db_session)
    _register_default_random_model(session=db_session, collection_id=collection.collection_id)
    registry = EmbedderRegistry()
    registry.register(embedder=_PathOnlyEmbedder())
    mocker.patch.object(embedder_registry, "get_registry", return_value=registry)

    with pytest.raises(embed_samples.ImageNotEmbeddedError, match="cannot be decoded"):
        embed_samples.embed_image_for_collection(
            session=db_session,
            collection_id=collection.collection_id,
            image_bytes=b"not an image",
        )


@pytest.mark.usefixtures("patched_registry")
def test_embed_text_for_collection(
    db_session: Session,
) -> None:
    """A text query is embedded via the registry with the collection's default model."""
    collection = create_collection(session=db_session)
    _register_default_random_model(
        session=db_session,
        collection_id=collection.collection_id,
        dimension=3,
    )

    embedding = embed_samples.embed_text_for_collection(
        session=db_session, collection_id=collection.collection_id, text="a red car"
    )

    assert len(embedding) == 3
    # Nothing is stored for an interactive query embedding.
    assert _stored_embeddings(session=db_session) == []


@pytest.mark.usefixtures("patched_registry")
def test_embed_text_for_collection__no_default_model(
    db_session: Session,
) -> None:
    """Without a default model the interactive text path raises a clear error."""
    collection = create_collection(session=db_session)
    with pytest.raises(ValueError, match="no default embedding model"):
        embed_samples.embed_text_for_collection(
            session=db_session, collection_id=collection.collection_id, text="a red car"
        )


def test_embed_text_for_collection__no_embedder_for_space_raises(
    db_session: Session,
    mocker: MockerFixture,
) -> None:
    """With a default model but no embedder for its space, the query raises."""
    collection = create_collection(session=db_session)
    _register_default_random_model(session=db_session, collection_id=collection.collection_id)
    # An empty registry cannot supply an embedder for the default model's space.
    mocker.patch.object(embedder_registry, "get_registry", return_value=EmbedderRegistry())

    with pytest.raises(MissingCapabilityError, match="cannot embed text"):
        embed_samples.embed_text_for_collection(
            session=db_session, collection_id=collection.collection_id, text="a red car"
        )


def test_embed_text_for_collection__no_embedding_raises(
    db_session: Session,
    mocker: MockerFixture,
) -> None:
    """When the embedder drops the text, the query raises instead of an IndexError."""
    collection = create_collection(session=db_session)
    _register_default_random_model(session=db_session, collection_id=collection.collection_id)
    registry = EmbedderRegistry()
    registry.register(embedder=_DropInputEmbedder())
    mocker.patch.object(embedder_registry, "get_registry", return_value=registry)

    with pytest.raises(ValueError, match="produced no embedding"):
        embed_samples.embed_text_for_collection(
            session=db_session, collection_id=collection.collection_id, text="a red car"
        )


@pytest.mark.usefixtures("patched_registry")
def test_embed_image_samples(
    db_session: Session,
) -> None:
    """Image samples are stored under the collection's default model, embedded by the registry."""
    collection = create_collection(session=db_session)
    samples = create_images(
        db_session=db_session,
        collection_id=collection.collection_id,
        images=[ImageStub(path="/test/a.jpg"), ImageStub(path="/test/b.jpg")],
    )
    model_id = _register_default_random_model(
        session=db_session, collection_id=collection.collection_id
    )
    sample_ids = [sample.sample_id for sample in samples]

    embed_samples.embed_image_samples(
        session=db_session, collection_id=collection.collection_id, sample_ids=sample_ids
    )

    count = sample_embedding_resolver.get_embedding_count(
        session=db_session, collection_id=collection.collection_id, embedding_model_id=model_id
    )
    assert count == len(sample_ids)


@pytest.mark.usefixtures("patched_registry")
def test_embed_image_samples__no_default_registers_registry_default(
    db_session: Session,
) -> None:
    """With no default model, the registry's image embedder is used and set as default."""
    collection = create_collection(session=db_session)
    samples = create_images(
        db_session=db_session,
        collection_id=collection.collection_id,
        images=[ImageStub(path="/test/a.jpg"), ImageStub(path="/test/b.jpg")],
    )
    sample_ids = [sample.sample_id for sample in samples]

    embed_samples.embed_image_samples(
        session=db_session, collection_id=collection.collection_id, sample_ids=sample_ids
    )

    # The registry embedder's space is registered as the collection's default.
    model_id = collection_embedding_model_resolver.get_default_by_collection_id(
        session=db_session, collection_id=collection.collection_id
    )
    assert model_id is not None
    count = sample_embedding_resolver.get_embedding_count(
        session=db_session, collection_id=collection.collection_id, embedding_model_id=model_id
    )
    assert count == len(sample_ids)


@pytest.mark.usefixtures("patched_registry")
def test_embed_image_samples__missing_id_bootstraps_no_default(
    db_session: Session,
) -> None:
    """A missing image ID raises before a default model is bootstrapped."""
    collection = create_collection(session=db_session)
    samples = create_images(
        db_session=db_session,
        collection_id=collection.collection_id,
        images=[ImageStub(path="/test/a.jpg")],
    )
    sample_ids = [samples[0].sample_id, uuid4()]

    with pytest.raises(ValueError, match="Could not fetch all image paths"):
        embed_samples.embed_image_samples(
            session=db_session, collection_id=collection.collection_id, sample_ids=sample_ids
        )

    # No default model is left behind and nothing is stored.
    model_id = collection_embedding_model_resolver.get_default_by_collection_id(
        session=db_session, collection_id=collection.collection_id
    )
    assert model_id is None
    assert _stored_embeddings(session=db_session) == []


def test_embed_image_samples__no_registered_embedder_skips(
    db_session: Session,
    mocker: MockerFixture,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """With a default model but no embedder for its space, embedding is skipped."""
    collection = create_collection(session=db_session)
    samples = create_images(
        db_session=db_session,
        collection_id=collection.collection_id,
        images=[ImageStub(path="/test/a.jpg"), ImageStub(path="/test/b.jpg")],
    )
    _register_default_random_model(session=db_session, collection_id=collection.collection_id)
    # An empty registry cannot supply an embedder for the default model's space.
    mocker.patch.object(embedder_registry, "get_registry", return_value=EmbedderRegistry())
    sample_ids = [sample.sample_id for sample in samples]

    with caplog.at_level(level=logging.WARNING):
        embed_samples.embed_image_samples(
            session=db_session, collection_id=collection.collection_id, sample_ids=sample_ids
        )

    assert "No embedding model loaded" in caplog.text
    assert _stored_embeddings(session=db_session) == []


def test_embed_image_samples__empty_ids_warns_and_skips(
    db_session: Session,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """An empty sample_ids list logs a warning and stores nothing."""
    collection = create_collection(session=db_session)

    with caplog.at_level(level=logging.WARNING):
        embed_samples.embed_image_samples(
            session=db_session, collection_id=collection.collection_id, sample_ids=[]
        )

    assert "No image samples to embed" in caplog.text
    assert _stored_embeddings(session=db_session) == []


@pytest.mark.usefixtures("patched_registry")
def test_embed_image_samples__enables_text_query(
    db_session: Session,
) -> None:
    """After the image embed registers a default, a text query resolves the same model.

    This mirrors the e2e flow of indexing then searching over the shared registry.
    """
    collection = create_collection(session=db_session)
    samples = create_images(
        db_session=db_session,
        collection_id=collection.collection_id,
        images=[ImageStub(path="/test/a.jpg"), ImageStub(path="/test/b.jpg")],
    )
    sample_ids = [sample.sample_id for sample in samples]

    embed_samples.embed_image_samples(
        session=db_session, collection_id=collection.collection_id, sample_ids=sample_ids
    )

    # The registry serves the text query with the default the image embed just registered.
    embedding = embed_samples.embed_text_for_collection(
        session=db_session, collection_id=collection.collection_id, text="a red car"
    )
    assert len(embedding) == 3


@pytest.mark.usefixtures("patched_registry")
def test_embed_annotation_collection(
    db_session: Session,
) -> None:
    """Annotation crops are stored under the collection's default model, via the registry."""
    annotation_collection_id = _create_annotation_collection(session=db_session)
    model_id = _register_default_random_model(
        session=db_session, collection_id=annotation_collection_id
    )

    embed_samples.embed_annotation_collection(
        session=db_session, annotation_collection_id=annotation_collection_id
    )

    count = sample_embedding_resolver.get_embedding_count(
        session=db_session, collection_id=annotation_collection_id, embedding_model_id=model_id
    )
    assert count == 1


@pytest.mark.usefixtures("patched_registry")
def test_embed_annotation_collection__no_default_registers_registry_default(
    db_session: Session,
) -> None:
    """With no default model, the registry's crop embedder is used and set as default."""
    annotation_collection_id = _create_annotation_collection(session=db_session)

    embed_samples.embed_annotation_collection(
        session=db_session, annotation_collection_id=annotation_collection_id
    )

    # The registry embedder's space is registered as the collection's default.
    model_id = collection_embedding_model_resolver.get_default_by_collection_id(
        session=db_session, collection_id=annotation_collection_id
    )
    assert model_id is not None
    count = sample_embedding_resolver.get_embedding_count(
        session=db_session, collection_id=annotation_collection_id, embedding_model_id=model_id
    )
    assert count == 1


def test_embed_annotation_collection__no_registered_embedder_skips(
    db_session: Session,
    mocker: MockerFixture,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """With a default model but no embedder for its space, annotation embedding is skipped."""
    annotation_collection_id = _create_annotation_collection(session=db_session)
    _register_default_random_model(session=db_session, collection_id=annotation_collection_id)
    # An empty registry cannot supply an embedder for the default model's space.
    mocker.patch.object(embedder_registry, "get_registry", return_value=EmbedderRegistry())

    with caplog.at_level(level=logging.WARNING):
        embed_samples.embed_annotation_collection(
            session=db_session, annotation_collection_id=annotation_collection_id
        )

    assert "No embedding model loaded" in caplog.text
    assert _stored_embeddings(session=db_session) == []


def test_embed_annotation_collection__stores_only_kept_crops(
    db_session: Session,
    mocker: MockerFixture,
) -> None:
    """Crops the embedder drops are left out, and kept vectors match their annotation IDs."""
    collection = create_collection(session=db_session)
    label = create_annotation_label(session=db_session, root_collection_id=collection.collection_id)
    # One annotation per image at a distinct box x, on ordered paths so the resolver returns
    # the crops in a known order (it sorts by image path).
    box_xs = [100, 200, 300]
    annotation_sample_ids = []
    for index, box_x in enumerate(box_xs):
        image = create_image(
            session=db_session,
            collection_id=collection.collection_id,
            file_path_abs=f"/path/to/sample_{index}.png",
        )
        annotation = create_annotation(
            session=db_session,
            collection_id=collection.collection_id,
            sample_id=image.sample_id,
            annotation_label_id=label.annotation_label_id,
            annotation_data={"x": box_x, "y": 0, "width": 20, "height": 20},
        )
        annotation_sample_ids.append(annotation.sample_id)
    annotation_collection_id = collection_resolver.get_or_create_child_collection(
        session=db_session,
        collection_id=collection.collection_id,
        sample_type=SampleType.ANNOTATION,
    )
    model_id = _register_default_random_model(
        session=db_session, collection_id=annotation_collection_id
    )
    registry = EmbedderRegistry()
    registry.register(embedder=_BoxXImageCropEmbedder())
    mocker.patch.object(embedder_registry, "get_registry", return_value=registry)

    embed_samples.embed_annotation_collection(
        session=db_session, annotation_collection_id=annotation_collection_id
    )

    # The embedder drops the last crop by path order, so only the first two are stored, each
    # with the vector encoding its box's left edge.
    rows = sample_embedding_resolver.get_by_sample_ids(
        session=db_session, sample_ids=annotation_sample_ids, embedding_model_id=model_id
    )
    stored = {row.sample_id: list(row.embedding) for row in rows}
    assert stored == {
        annotation_sample_ids[0]: [box_xs[0]] * 3,
        annotation_sample_ids[1]: [box_xs[1]] * 3,
    }


def test_embed_video_samples(
    db_session: Session,
    mocker: MockerFixture,
) -> None:
    """The registry embedder's vectors are stored against the matching video sample IDs."""
    video_collection = create_collection(session=db_session, sample_type=SampleType.VIDEO)
    video_ids = create_videos(
        session=db_session,
        collection_id=video_collection.collection_id,
        videos=[
            VideoStub(path="/videos/video_0.mp4"),
            VideoStub(path="/videos/video_1.mp4"),
            VideoStub(path="/videos/video_2.mp4"),
        ],
    )
    model_id = _register_default_random_model(
        session=db_session,
        collection_id=video_collection.collection_id,
        dimension=2,
    )
    registry = EmbedderRegistry()
    registry.register(embedder=_PathIndexVideoEmbedder())
    mocker.patch.object(embedder_registry, "get_registry", return_value=registry)

    embed_samples.embed_video_samples(
        session=db_session, collection_id=video_collection.collection_id, sample_ids=video_ids
    )

    # The embedder drops the last video, so only the first two are stored, each with the
    # vector encoding the number parsed from its resolved path.
    rows = sample_embedding_resolver.get_by_sample_ids(
        session=db_session, sample_ids=video_ids, embedding_model_id=model_id
    )
    stored = {row.sample_id: list(row.embedding) for row in rows}
    assert stored == {video_ids[0]: [0.0, 0.0], video_ids[1]: [1.0, 1.0]}


@pytest.mark.usefixtures("patched_registry")
def test_embed_video_samples__no_default_registers_registry_default(
    db_session: Session,
) -> None:
    """With no default model, the registry's video embedder is used and set as default."""
    video_collection = create_collection(session=db_session, sample_type=SampleType.VIDEO)
    video_ids = create_videos(
        session=db_session,
        collection_id=video_collection.collection_id,
        videos=[VideoStub(path="/videos/video_0.mp4"), VideoStub(path="/videos/video_1.mp4")],
    )

    embed_samples.embed_video_samples(
        session=db_session, collection_id=video_collection.collection_id, sample_ids=video_ids
    )

    # The registry embedder's space is registered as the collection's default.
    model_id = collection_embedding_model_resolver.get_default_by_collection_id(
        session=db_session, collection_id=video_collection.collection_id
    )
    assert model_id is not None
    count = sample_embedding_resolver.get_embedding_count(
        session=db_session,
        collection_id=video_collection.collection_id,
        embedding_model_id=model_id,
    )
    assert count == len(video_ids)


@pytest.mark.usefixtures("patched_registry")
def test_embed_video_samples__missing_id_bootstraps_no_default(
    db_session: Session,
) -> None:
    """A missing video ID raises before a default model is bootstrapped."""
    video_collection = create_collection(session=db_session, sample_type=SampleType.VIDEO)
    video_ids = create_videos(
        session=db_session,
        collection_id=video_collection.collection_id,
        videos=[VideoStub(path="/videos/video_0.mp4")],
    )
    sample_ids = [video_ids[0], uuid4()]

    with pytest.raises(ValueError, match="Could not fetch all video paths"):
        embed_samples.embed_video_samples(
            session=db_session, collection_id=video_collection.collection_id, sample_ids=sample_ids
        )

    # No default model is left behind and nothing is stored.
    model_id = collection_embedding_model_resolver.get_default_by_collection_id(
        session=db_session, collection_id=video_collection.collection_id
    )
    assert model_id is None
    assert _stored_embeddings(session=db_session) == []


def test_embed_video_samples__no_registered_embedder_skips(
    db_session: Session,
    mocker: MockerFixture,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """With a default model but no embedder for its space, video embedding is skipped."""
    video_collection = create_collection(session=db_session, sample_type=SampleType.VIDEO)
    video_ids = create_videos(
        session=db_session,
        collection_id=video_collection.collection_id,
        videos=[VideoStub(path="/videos/video_0.mp4")],
    )
    _register_default_random_model(session=db_session, collection_id=video_collection.collection_id)
    # An empty registry cannot supply an embedder for the default model's space.
    mocker.patch.object(embedder_registry, "get_registry", return_value=EmbedderRegistry())

    with caplog.at_level(level=logging.WARNING):
        embed_samples.embed_video_samples(
            session=db_session, collection_id=video_collection.collection_id, sample_ids=video_ids
        )

    assert "No embedding model loaded" in caplog.text
    assert _stored_embeddings(session=db_session) == []


def test_embed_video_samples__empty_ids_warns_and_skips(
    db_session: Session,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """An empty sample_ids list logs a warning and stores nothing."""
    video_collection = create_collection(session=db_session, sample_type=SampleType.VIDEO)

    with caplog.at_level(level=logging.WARNING):
        embed_samples.embed_video_samples(
            session=db_session, collection_id=video_collection.collection_id, sample_ids=[]
        )

    assert "No video samples to embed" in caplog.text
    assert _stored_embeddings(session=db_session) == []


def test_embed_frame_samples(
    db_session: Session,
    mocker: MockerFixture,
) -> None:
    """The registry embedder's vectors are stored against the matching frame sample IDs."""
    video_collection = create_collection(session=db_session, sample_type=SampleType.VIDEO)
    frames = create_video_with_frames(
        session=db_session,
        collection_id=video_collection.collection_id,
        video=VideoStub(duration_s=1.0, fps=3.0),
    )
    model_id = _register_default_random_model(
        session=db_session,
        collection_id=frames.video_frames_collection_id,
    )
    # One distinct color per frame, so the stored vector identifies its source frame.
    colors = [(10, 20, 30), (40, 50, 60), (70, 80, 90)]
    assert len(frames.frame_sample_ids) == len(colors)
    pil_frames = [Image.new(mode="RGB", size=(2, 2), color=color) for color in colors]
    registry = EmbedderRegistry()
    registry.register(embedder=_FirstPixelPILEmbedder())
    mocker.patch.object(embedder_registry, "get_registry", return_value=registry)

    embed_samples.embed_frame_samples(
        session=db_session,
        collection_id=frames.video_frames_collection_id,
        sample_ids=frames.frame_sample_ids,
        pil_frames=pil_frames,
    )

    # The embedder drops the last frame, so only the first two are stored, each with the
    # vector encoding its top-left pixel.
    rows = sample_embedding_resolver.get_by_sample_ids(
        session=db_session, sample_ids=frames.frame_sample_ids, embedding_model_id=model_id
    )
    stored = {row.sample_id: list(row.embedding) for row in rows}
    assert stored == {
        frames.frame_sample_ids[0]: list(colors[0]),
        frames.frame_sample_ids[1]: list(colors[1]),
    }


@pytest.mark.usefixtures("patched_registry")
def test_embed_frame_samples__no_default_registers_registry_default(
    db_session: Session,
) -> None:
    """With no default model, the registry's PIL embedder is used and set as default."""
    video_collection = create_collection(session=db_session, sample_type=SampleType.VIDEO)
    frames = create_video_with_frames(
        session=db_session,
        collection_id=video_collection.collection_id,
        video=VideoStub(duration_s=1.0, fps=3.0),
    )
    pil_frames = [Image.new(mode="RGB", size=(2, 2)) for _ in frames.frame_sample_ids]

    embed_samples.embed_frame_samples(
        session=db_session,
        collection_id=frames.video_frames_collection_id,
        sample_ids=frames.frame_sample_ids,
        pil_frames=pil_frames,
    )

    # The registry embedder's space is registered as the collection's default.
    model_id = collection_embedding_model_resolver.get_default_by_collection_id(
        session=db_session, collection_id=frames.video_frames_collection_id
    )
    assert model_id is not None
    count = sample_embedding_resolver.get_embedding_count(
        session=db_session,
        collection_id=frames.video_frames_collection_id,
        embedding_model_id=model_id,
    )
    assert count == len(frames.frame_sample_ids)


def test_embed_frame_samples__no_registered_embedder_skips(
    db_session: Session,
    mocker: MockerFixture,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """With a default model but no embedder for its space, frame embedding is skipped."""
    video_collection = create_collection(session=db_session, sample_type=SampleType.VIDEO)
    frames = create_video_with_frames(
        session=db_session,
        collection_id=video_collection.collection_id,
        video=VideoStub(duration_s=1.0, fps=3.0),
    )
    _register_default_random_model(
        session=db_session,
        collection_id=frames.video_frames_collection_id,
    )
    pil_frames = [Image.new(mode="RGB", size=(2, 2)) for _ in frames.frame_sample_ids]
    # An empty registry cannot supply an embedder for the default model's space.
    mocker.patch.object(embedder_registry, "get_registry", return_value=EmbedderRegistry())

    with caplog.at_level(level=logging.WARNING):
        embed_samples.embed_frame_samples(
            session=db_session,
            collection_id=frames.video_frames_collection_id,
            sample_ids=frames.frame_sample_ids,
            pil_frames=pil_frames,
        )

    assert "No embedding model loaded" in caplog.text
    assert _stored_embeddings(session=db_session) == []


def test_embed_frame_samples__empty_ids_warns_and_skips(
    db_session: Session,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """An empty sample_ids list logs a warning and stores nothing."""
    video_collection = create_collection(session=db_session, sample_type=SampleType.VIDEO)
    frames = create_video_with_frames(
        session=db_session,
        collection_id=video_collection.collection_id,
        video=VideoStub(duration_s=1.0, fps=3.0),
    )

    with caplog.at_level(level=logging.WARNING):
        embed_samples.embed_frame_samples(
            session=db_session,
            collection_id=frames.video_frames_collection_id,
            sample_ids=[],
            pil_frames=[],
        )

    assert "No frame samples to embed" in caplog.text
    assert _stored_embeddings(session=db_session) == []


def test_embed_frame_samples__count_mismatch_raises(
    db_session: Session,
) -> None:
    """A mismatch between sample IDs and frames raises before any embedding."""
    video_collection = create_collection(session=db_session, sample_type=SampleType.VIDEO)
    frames = create_video_with_frames(
        session=db_session,
        collection_id=video_collection.collection_id,
        video=VideoStub(duration_s=1.0, fps=3.0),
    )
    # One fewer frame than sample IDs.
    pil_frames = [Image.new(mode="RGB", size=(2, 2)) for _ in frames.frame_sample_ids[:-1]]

    with pytest.raises(ValueError, match="does not match number of frames"):
        embed_samples.embed_frame_samples(
            session=db_session,
            collection_id=frames.video_frames_collection_id,
            sample_ids=frames.frame_sample_ids,
            pil_frames=pil_frames,
        )

    assert _stored_embeddings(session=db_session) == []


@pytest.mark.usefixtures("patched_registry")
def test_has_frame_embedder__true_when_embedder_available(db_session: Session) -> None:
    """The guard reports True when the registry can supply a frame embedder."""
    collection = create_collection(session=db_session, sample_type=SampleType.VIDEO_FRAME)

    assert (
        embed_samples.has_frame_embedder(session=db_session, collection_id=collection.collection_id)
        is True
    )


def test_has_frame_embedder__false_when_default_space_unavailable(
    db_session: Session, mocker: MockerFixture
) -> None:
    """The guard reports False when no embedder matches the collection's default space.

    The registry can still supply a bootstrap embedder for a different space, so the result
    must follow the collection's default model rather than mere registry availability.
    """
    registry = EmbedderRegistry()
    registry.register(embedder=RandomEmbedder(dimension=3))
    mocker.patch.object(embedder_registry, "get_registry", return_value=registry)
    collection = create_collection(session=db_session, sample_type=SampleType.VIDEO_FRAME)
    create_embedding_model(
        session=db_session,
        collection_id=collection.collection_id,
        embedding_model_name="other_space",
        embedding_dimension=3,
        set_as_default=True,
    )

    assert (
        embed_samples.has_frame_embedder(session=db_session, collection_id=collection.collection_id)
        is False
    )


def _register_default_random_model(
    session: Session,
    collection_id: UUID,
    dimension: int = 3,
    url: str | None = None,
) -> UUID:
    """Register the random embedder's space as the collection's default and return its model ID.

    A given ``url`` is stored as the model's remote embedder URL.
    """
    model = create_embedding_model(
        session=session,
        collection_id=collection_id,
        embedding_model_name="random_model",
        embedding_dimension=dimension,
        set_as_default=True,
    )
    if url is not None:
        model.remote_embedder_url = url
        session.add(model)
        session.commit()
    return model.embedding_model_id


def _create_annotation_collection(session: Session) -> UUID:
    """Create a collection with one annotated image and return its annotation child collection."""
    collection = create_collection(session=session)
    image = create_image(session=session, collection_id=collection.collection_id)
    label = create_annotation_label(session=session, root_collection_id=collection.collection_id)
    create_annotation(
        session=session,
        collection_id=collection.collection_id,
        sample_id=image.sample_id,
        annotation_label_id=label.annotation_label_id,
    )
    return collection_resolver.get_or_create_child_collection(
        session=session,
        collection_id=collection.collection_id,
        sample_type=SampleType.ANNOTATION,
    )


def _stored_embeddings(session: Session) -> list[SampleEmbeddingTable]:
    """Return every stored sample embedding, for asserting the skip path stores nothing."""
    return list(session.exec(select(SampleEmbeddingTable)).all())


def _path_number(path: str) -> float:
    """Return the number in a ``/videos/video_<n>.mp4`` path."""
    match = re.search(r"(\d+)", path)
    assert match is not None
    return float(match.group(1))


def _png_bytes(color: tuple[int, int, int] = (0, 0, 0)) -> bytes:
    """Encode a one-pixel PNG of the given RGB color, as an image upload carries it.

    Args:
        color: RGB value of the single pixel.

    Returns:
        The encoded PNG bytes.
    """
    buffer = io.BytesIO()
    Image.new(mode="RGB", size=(1, 1), color=color).save(buffer, format="PNG")
    return buffer.getvalue()
