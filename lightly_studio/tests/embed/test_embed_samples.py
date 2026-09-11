"""Tests for the class-free embed_samples interface."""

from __future__ import annotations

import logging
from uuid import UUID

import numpy as np
import pytest
from numpy.typing import NDArray
from PIL import Image
from pytest_mock import MockerFixture
from sqlmodel import Session, select

from lightly_studio.dataset import embedding_manager
from lightly_studio.dataset.embedding_generator import RandomEmbeddingGenerator
from lightly_studio.dataset.embedding_manager import (
    EmbeddingManager,
    EmbeddingManagerProvider,
)
from lightly_studio.embed import embed_samples, embedder_registry
from lightly_studio.embed.embedder_registry import EmbedderRegistry
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
    create_image,
    create_images,
)
from tests.resolvers.video.helpers import (
    VideoStub,
    create_video_with_frames,
    create_videos,
)


class _FirstPixelEmbeddingGenerator(RandomEmbeddingGenerator):
    """Embeds each PIL image as its top-left pixel's RGB, so frame order is verifiable."""

    def embed_pil_images(
        self, images: list[Image.Image], show_progress: bool = True
    ) -> NDArray[np.float32]:
        _ = show_progress
        return np.array([image.getpixel((0, 0)) for image in images], dtype=np.float32)


@pytest.fixture
def patched_manager(mocker: MockerFixture) -> EmbeddingManager:
    """Route embed_samples to a fresh manager so tests never touch the shared singleton."""
    manager = EmbeddingManager()
    mocker.patch.object(EmbeddingManagerProvider, "get_embedding_manager", return_value=manager)
    return manager


@pytest.fixture
def patched_registry(mocker: MockerFixture) -> EmbedderRegistry:
    """Route embed_samples to a fresh registry so tests never touch the shared singleton."""
    registry = EmbedderRegistry()
    registry.register(embedder=RandomEmbedder())
    mocker.patch.object(embedder_registry, "get_registry", return_value=registry)
    return registry


def test_embed_image_for_collection(
    db_session: Session,
    patched_manager: EmbeddingManager,
) -> None:
    """A single image is embedded with the collection's default model, unstored."""
    collection = create_collection(session=db_session)
    _register_default_random_model(
        manager=patched_manager,
        session=db_session,
        collection_id=collection.collection_id,
        dimension=5,
    )

    embedding = embed_samples.embed_image_for_collection(
        collection_id=collection.collection_id, filepath="/path/to/image.jpg"
    )

    assert len(embedding) == 5
    # Nothing is stored for an interactive query embedding.
    assert _stored_embeddings(session=db_session) == []


@pytest.mark.usefixtures("patched_manager")
def test_embed_image_for_collection__no_default_model(
    db_session: Session,
) -> None:
    """Without a default model the interactive image path raises a clear error."""
    collection = create_collection(session=db_session)
    with pytest.raises(ValueError, match="No embedding_model_id provided and no default embedding"):
        embed_samples.embed_image_for_collection(
            collection_id=collection.collection_id, filepath="/path/to/image.jpg"
        )


def test_embed_text_for_collection(
    db_session: Session,
    patched_manager: EmbeddingManager,
) -> None:
    """A text query is embedded with the collection's default model."""
    collection = create_collection(session=db_session)
    _register_default_random_model(
        manager=patched_manager,
        session=db_session,
        collection_id=collection.collection_id,
        dimension=3,
    )

    embedding = embed_samples.embed_text_for_collection(
        collection_id=collection.collection_id, text="a red car"
    )

    assert len(embedding) == 3


@pytest.mark.usefixtures("patched_manager")
def test_embed_text_for_collection__no_default_model(
    db_session: Session,
) -> None:
    """Without a default model the interactive text path raises a clear error."""
    collection = create_collection(session=db_session)
    with pytest.raises(ValueError, match="No embedding_model_id provided and no default embedding"):
        embed_samples.embed_text_for_collection(
            collection_id=collection.collection_id, text="a red car"
        )


@pytest.mark.usefixtures("patched_registry")
def test_embed_image_samples(
    db_session: Session,
    patched_manager: EmbeddingManager,
) -> None:
    """Image samples are stored under the collection's default model, embedded by the registry."""
    collection = create_collection(session=db_session)
    samples = create_images(
        db_session=db_session,
        collection_id=collection.collection_id,
        images=[ImageStub(path="/test/a.jpg"), ImageStub(path="/test/b.jpg")],
    )
    model_id = _register_default_random_model(
        manager=patched_manager, session=db_session, collection_id=collection.collection_id
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


def test_embed_image_samples__no_registered_embedder_skips(
    db_session: Session,
    patched_manager: EmbeddingManager,
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
    _register_default_random_model(
        manager=patched_manager, session=db_session, collection_id=collection.collection_id
    )
    # An empty registry cannot supply an embedder for the default model's space.
    mocker.patch.object(embedder_registry, "get_registry", return_value=EmbedderRegistry())
    sample_ids = [sample.sample_id for sample in samples]

    with caplog.at_level(level=logging.WARNING):
        embed_samples.embed_image_samples(
            session=db_session, collection_id=collection.collection_id, sample_ids=sample_ids
        )

    assert "No embedding model loaded" in caplog.text
    assert _stored_embeddings(session=db_session) == []


def test_embed_annotation_collection(
    db_session: Session,
    patched_manager: EmbeddingManager,
) -> None:
    """Annotation crops are embedded and stored under the collection's default model."""
    collection = create_collection(session=db_session)
    image = create_image(session=db_session, collection_id=collection.collection_id)
    label = create_annotation_label(session=db_session, root_collection_id=collection.collection_id)
    create_annotation(
        session=db_session,
        collection_id=collection.collection_id,
        sample_id=image.sample_id,
        annotation_label_id=label.annotation_label_id,
    )
    annotation_collection_id = collection_resolver.get_or_create_child_collection(
        session=db_session,
        collection_id=collection.collection_id,
        sample_type=SampleType.ANNOTATION,
    )
    model_id = _register_default_random_model(
        manager=patched_manager, session=db_session, collection_id=annotation_collection_id
    )

    embed_samples.embed_annotation_collection(
        session=db_session, annotation_collection_id=annotation_collection_id
    )

    count = sample_embedding_resolver.get_embedding_count(
        session=db_session, collection_id=annotation_collection_id, embedding_model_id=model_id
    )
    assert count == 1


@pytest.mark.usefixtures("patched_manager")
def test_embed_annotation_collection__no_default_model_skips(
    db_session: Session,
    mocker: MockerFixture,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """With no default model, annotation embedding is skipped and nothing stored."""
    collection = create_collection(session=db_session)
    annotation_collection_id = collection_resolver.get_or_create_child_collection(
        session=db_session,
        collection_id=collection.collection_id,
        sample_type=SampleType.ANNOTATION,
    )
    _disable_env_loader(mocker=mocker)

    with caplog.at_level(level=logging.WARNING):
        embed_samples.embed_annotation_collection(
            session=db_session, annotation_collection_id=annotation_collection_id
        )

    assert "No embedding model loaded" in caplog.text
    assert _stored_embeddings(session=db_session) == []


def test_embed_video_samples(
    db_session: Session,
    patched_manager: EmbeddingManager,
) -> None:
    """Video samples are embedded and stored under the collection's default model."""
    video_collection = create_collection(session=db_session, sample_type=SampleType.VIDEO)
    video_ids = create_videos(
        session=db_session,
        collection_id=video_collection.collection_id,
        videos=[VideoStub(path="/videos/video_0.mp4"), VideoStub(path="/videos/video_1.mp4")],
    )
    model_id = _register_default_random_model(
        manager=patched_manager, session=db_session, collection_id=video_collection.collection_id
    )

    embed_samples.embed_video_samples(
        session=db_session, collection_id=video_collection.collection_id, sample_ids=video_ids
    )

    count = sample_embedding_resolver.get_embedding_count(
        session=db_session,
        collection_id=video_collection.collection_id,
        embedding_model_id=model_id,
    )
    assert count == len(video_ids)


@pytest.mark.usefixtures("patched_manager")
def test_embed_video_samples__no_default_model_skips(
    db_session: Session,
    mocker: MockerFixture,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """With no default model, video embedding is skipped and nothing stored."""
    video_collection = create_collection(session=db_session, sample_type=SampleType.VIDEO)
    video_ids = create_videos(
        session=db_session,
        collection_id=video_collection.collection_id,
        videos=[VideoStub(path="/videos/video_0.mp4")],
    )
    _disable_env_loader(mocker=mocker)

    with caplog.at_level(level=logging.WARNING):
        embed_samples.embed_video_samples(
            session=db_session, collection_id=video_collection.collection_id, sample_ids=video_ids
        )

    assert "No embedding model loaded" in caplog.text
    assert _stored_embeddings(session=db_session) == []


def test_embed_frame_samples(
    db_session: Session,
    patched_manager: EmbeddingManager,
) -> None:
    """Video frames are embedded and stored for the given frame sample IDs."""
    video_collection = create_collection(session=db_session, sample_type=SampleType.VIDEO)
    frames = create_video_with_frames(
        session=db_session,
        collection_id=video_collection.collection_id,
        video=VideoStub(duration_s=1.0, fps=3.0),
    )
    model_id = _register_default_random_model(
        manager=patched_manager,
        session=db_session,
        collection_id=frames.video_frames_collection_id,
    )
    pil_frames = [Image.new("RGB", (2, 2)) for _ in frames.frame_sample_ids]

    embed_samples.embed_frame_samples(
        session=db_session,
        collection_id=frames.video_frames_collection_id,
        sample_ids=frames.frame_sample_ids,
        pil_frames=pil_frames,
    )

    count = sample_embedding_resolver.get_embedding_count(
        session=db_session,
        collection_id=frames.video_frames_collection_id,
        embedding_model_id=model_id,
    )
    assert count == len(frames.frame_sample_ids)


def test_embed_frame_samples__matches_frames_to_sample_ids_in_order(
    db_session: Session,
    patched_manager: EmbeddingManager,
) -> None:
    """Each frame's embedding is stored against the sample ID at the same position."""
    video_collection = create_collection(session=db_session, sample_type=SampleType.VIDEO)
    frames = create_video_with_frames(
        session=db_session,
        collection_id=video_collection.collection_id,
        video=VideoStub(duration_s=1.0, fps=3.0),
    )
    # One distinct color per frame, so the stored vector identifies its source frame.
    colors = [(10, 20, 30), (40, 50, 60), (70, 80, 90)]
    assert len(frames.frame_sample_ids) == len(colors)
    pil_frames = [Image.new("RGB", (2, 2), color=color) for color in colors]

    model_id = patched_manager.register_embedding_model(
        session=db_session,
        embedding_generator=_FirstPixelEmbeddingGenerator(),
        collection_id=frames.video_frames_collection_id,
        set_as_default=True,
    ).embedding_model_id

    embed_samples.embed_frame_samples(
        session=db_session,
        collection_id=frames.video_frames_collection_id,
        sample_ids=frames.frame_sample_ids,
        pil_frames=pil_frames,
    )

    rows = sample_embedding_resolver.get_by_sample_ids(
        session=db_session, sample_ids=frames.frame_sample_ids, embedding_model_id=model_id
    )
    assert len(rows) == len(colors)
    for row, color in zip(rows, colors):
        assert list(row.embedding) == pytest.approx(list(color))


@pytest.mark.usefixtures("patched_manager")
def test_embed_frame_samples__no_default_model_skips(
    db_session: Session,
    mocker: MockerFixture,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """With no default model, frame embedding is skipped and nothing stored."""
    video_collection = create_collection(session=db_session, sample_type=SampleType.VIDEO)
    frames = create_video_with_frames(
        session=db_session,
        collection_id=video_collection.collection_id,
        video=VideoStub(duration_s=1.0, fps=3.0),
    )
    pil_frames = [Image.new("RGB", (2, 2)) for _ in frames.frame_sample_ids]
    _disable_env_loader(mocker=mocker)

    with caplog.at_level(level=logging.WARNING):
        embed_samples.embed_frame_samples(
            session=db_session,
            collection_id=frames.video_frames_collection_id,
            sample_ids=frames.frame_sample_ids,
            pil_frames=pil_frames,
        )

    assert "No embedding model loaded" in caplog.text
    assert _stored_embeddings(session=db_session) == []


@pytest.mark.usefixtures("patched_manager")
def test_collection_has_default_embedder__loads_and_reports_true(
    db_session: Session,
    mocker: MockerFixture,
) -> None:
    """The helper ensures the default is loaded, then reports it is available.

    The check is ensure-and-check: no default exists up front, and the first call
    registers one as a side effect before returning True.
    """
    collection = create_collection(session=db_session)
    mocker.patch.object(
        embedding_manager,
        "_load_embedding_generator_from_env",
        return_value=RandomEmbeddingGenerator(),
    )
    # No default embedding model exists before the call.
    assert (
        collection_embedding_model_resolver.get_default_by_collection_id(
            session=db_session, collection_id=collection.collection_id
        )
        is None
    )

    has_default = embed_samples.collection_has_default_embedder(
        session=db_session, collection_id=collection.collection_id
    )

    assert has_default is True
    # The call registered a default model as its side effect.
    assert (
        collection_embedding_model_resolver.get_default_by_collection_id(
            session=db_session, collection_id=collection.collection_id
        )
        is not None
    )


@pytest.mark.usefixtures("patched_manager")
def test_collection_has_default_embedder__false_when_none_loadable(
    db_session: Session,
    mocker: MockerFixture,
) -> None:
    """The helper reports False when no default model can be loaded."""
    collection = create_collection(session=db_session)
    _disable_env_loader(mocker=mocker)

    has_default = embed_samples.collection_has_default_embedder(
        session=db_session, collection_id=collection.collection_id
    )

    assert has_default is False
    assert (
        collection_embedding_model_resolver.get_default_by_collection_id(
            session=db_session, collection_id=collection.collection_id
        )
        is None
    )


def _register_default_random_model(
    manager: EmbeddingManager,
    session: Session,
    collection_id: UUID,
    dimension: int = 3,
) -> UUID:
    """Register a random embedding generator as the collection's default and return its model ID."""
    return manager.register_embedding_model(
        session=session,
        embedding_generator=RandomEmbeddingGenerator(dimension=dimension),
        collection_id=collection_id,
        set_as_default=True,
    ).embedding_model_id


def _disable_env_loader(mocker: MockerFixture) -> None:
    """Make loading a default generator from the environment return nothing."""
    mocker.patch.object(embedding_manager, "_load_embedding_generator_from_env", return_value=None)


def _stored_embeddings(session: Session) -> list[SampleEmbeddingTable]:
    """Return every stored sample embedding, for asserting the skip path stores nothing."""
    return list(session.exec(select(SampleEmbeddingTable)).all())
