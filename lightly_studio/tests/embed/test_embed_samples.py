"""Tests for the class-free embed_samples interface."""

from __future__ import annotations

import logging
import re
from uuid import UUID, uuid4

import numpy as np
import pytest
from lightly_studio_serve.embedder import (
    Embedder,
    ImageBytesEmbedder,
    ImagePathEmbedder,
    ImagePILEmbedder,
    TextEmbedder,
    VideoPathEmbedder,
)
from lightly_studio_serve.types import EmbeddingResult, EmbeddingSpaceSpec
from PIL import Image
from pytest_mock import MockerFixture
from sqlmodel import Session, select

from lightly_studio.embed import embed_samples, embedder_registry
from lightly_studio.embed.embedder_registry import EmbedderRegistry
from lightly_studio.embed.errors import MissingCapabilityError
from lightly_studio.embed.random_embedder import RandomEmbedder
from lightly_studio.models.collection import SampleType
from lightly_studio.models.sample_embedding import SampleEmbeddingTable
from lightly_studio.resolvers import (
    collection_embedding_model_resolver,
    sample_embedding_resolver,
)
from tests.helpers_resolvers import (
    ImageStub,
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


class _PathOnlyEmbedder(ImagePathEmbedder):
    """Embeds each image path as zeros.

    Shares the random model's space so it resolves as the collection's default.
    """

    __slots__ = ()

    def embedding_space_spec(self) -> EmbeddingSpaceSpec:
        """Describe the shared random embedding space with dimension 3."""
        return EmbeddingSpaceSpec(space_key="random_model", dimension=3)

    def embed_images(self, paths: list[str]) -> EmbeddingResult:
        """Embed each image path as zeros."""
        return EmbeddingResult(
            embeddings=np.zeros((len(paths), 3), dtype=np.float32),
            kept_indices=list(range(len(paths))),
        )


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

    with pytest.raises(MissingCapabilityError, match="has no ImageBytesEmbedder"):
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


@pytest.mark.parametrize("embedder", [_PathOnlyEmbedder(), _PILOnlyEmbedder()])
def test_embed_image_for_collection__no_bytes_capability_raises(
    db_session: Session,
    mocker: MockerFixture,
    embedder: Embedder,
) -> None:
    """An embedder without the bytes capability does not serve image search."""
    collection = create_collection(session=db_session)
    _register_default_random_model(session=db_session, collection_id=collection.collection_id)
    registry = EmbedderRegistry()
    registry.register(embedder=embedder)
    mocker.patch.object(embedder_registry, "get_registry", return_value=registry)

    with pytest.raises(MissingCapabilityError, match="has no ImageBytesEmbedder"):
        embed_samples.embed_image_for_collection(
            session=db_session,
            collection_id=collection.collection_id,
            image_bytes=b"broken image",
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

    with pytest.raises(MissingCapabilityError, match="has no TextEmbedder"):
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


def test_embed_mcap_image_frames(
    db_session: Session,
    mocker: MockerFixture,
) -> None:
    """Each sample stores the unit-length mean of its frame embeddings."""
    collection = create_collection(session=db_session)
    images = create_images(
        db_session=db_session,
        collection_id=collection.collection_id,
        images=[ImageStub(path="a.png"), ImageStub(path="b.png"), ImageStub(path="c.png")],
    )
    sample_ids = [image.sample_id for image in images]
    model_id = _register_default_random_model(
        session=db_session, collection_id=collection.collection_id
    )
    registry = EmbedderRegistry()
    registry.register(embedder=_PILOnlyEmbedder())
    mocker.patch.object(embedder_registry, "get_registry", return_value=registry)
    # The embedder embeds a frame as its top-left pixel. The mean of (3, 0, 0) and
    # (0, 4, 0) is (1.5, 2, 0), of length 2.5. The second sample has no frames.
    frames_by_sample_id = {
        sample_ids[0]: [
            Image.new(mode="RGB", size=(2, 2), color=(3, 0, 0)),
            Image.new(mode="RGB", size=(2, 2), color=(0, 4, 0)),
        ],
        sample_ids[1]: [],
        sample_ids[2]: [Image.new(mode="RGB", size=(2, 2), color=(0, 0, 2))],
    }

    embed_samples.embed_mcap_image_frames(
        session=db_session,
        collection_id=collection.collection_id,
        sample_ids=sample_ids,
        load_frames=lambda sample_id: frames_by_sample_id[sample_id],
    )

    rows = sample_embedding_resolver.get_by_sample_ids(
        session=db_session, sample_ids=sample_ids, embedding_model_id=model_id
    )
    stored = {row.sample_id: list(row.embedding) for row in rows}
    assert stored.keys() == {sample_ids[0], sample_ids[2]}
    assert stored[sample_ids[0]] == pytest.approx([0.6, 0.8, 0.0])
    assert stored[sample_ids[2]] == pytest.approx([0.0, 0.0, 1.0])


def test_embed_mcap_image_frames__no_registered_embedder_loads_no_frames(
    db_session: Session,
    mocker: MockerFixture,
) -> None:
    """With no embedder for the default model's space, no frame is loaded or stored."""
    collection = create_collection(session=db_session)
    image = create_image(session=db_session, collection_id=collection.collection_id)
    _register_default_random_model(session=db_session, collection_id=collection.collection_id)
    mocker.patch.object(embedder_registry, "get_registry", return_value=EmbedderRegistry())
    load_frames = mocker.Mock(return_value=[])

    embed_samples.embed_mcap_image_frames(
        session=db_session,
        collection_id=collection.collection_id,
        sample_ids=[image.sample_id],
        load_frames=load_frames,
    )

    load_frames.assert_not_called()
    assert _stored_embeddings(session=db_session) == []


def test_embed_mcap_image_frames__empty_ids_warns_and_skips(
    db_session: Session,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """An empty sample_ids list logs a warning and stores nothing."""
    collection = create_collection(session=db_session, sample_type=SampleType.SEQUENCE)

    with caplog.at_level(level=logging.WARNING):
        embed_samples.embed_mcap_image_frames(
            session=db_session,
            collection_id=collection.collection_id,
            sample_ids=[],
            load_frames=lambda _: [],
        )

    assert "No samples to embed" in caplog.text
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
) -> UUID:
    """Register the random embedder's space as the collection's default and return its model ID."""
    model = create_embedding_model(
        session=session,
        collection_id=collection_id,
        embedding_model_name="random_model",
        embedding_dimension=dimension,
        set_as_default=True,
    )
    return model.embedding_model_id


def _stored_embeddings(session: Session) -> list[SampleEmbeddingTable]:
    """Return every stored sample embedding, for asserting the skip path stores nothing."""
    return list(session.exec(select(SampleEmbeddingTable)).all())


def _path_number(path: str) -> float:
    """Return the number in a ``/videos/video_<n>.mp4`` path."""
    match = re.search(r"(\d+)", path)
    assert match is not None
    return float(match.group(1))
