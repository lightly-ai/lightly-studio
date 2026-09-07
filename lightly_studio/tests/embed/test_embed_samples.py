"""Tests for the class-free embed_samples interface."""

from __future__ import annotations

import logging
from uuid import UUID

import pytest
from pytest_mock import MockerFixture
from sqlmodel import Session, select

from lightly_studio.dataset import embedding_manager
from lightly_studio.dataset.embedding_generator import RandomEmbeddingGenerator
from lightly_studio.dataset.embedding_manager import (
    EmbeddingManager,
    EmbeddingManagerProvider,
)
from lightly_studio.embed import embed_samples
from lightly_studio.models.collection import CollectionTable, SampleType
from lightly_studio.models.image import ImageTable
from lightly_studio.models.sample_embedding import SampleEmbeddingTable
from lightly_studio.resolvers import (
    collection_resolver,
    sample_embedding_resolver,
)
from tests.helpers_resolvers import (
    create_annotation,
    create_annotation_label,
    create_collection,
    create_image,
)


@pytest.fixture
def patched_manager(mocker: MockerFixture) -> EmbeddingManager:
    """Route embed_samples to a fresh manager so tests never touch the shared singleton."""
    manager = EmbeddingManager()
    mocker.patch.object(EmbeddingManagerProvider, "get_embedding_manager", return_value=manager)
    return manager


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
    assert _stored_embeddings(db_session) == []


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


def test_embed_image_samples(
    db_session: Session,
    collection: CollectionTable,
    samples: list[ImageTable],
    patched_manager: EmbeddingManager,
) -> None:
    """Image samples are embedded and stored under the collection's default model."""
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


@pytest.mark.usefixtures("patched_manager")
def test_embed_image_samples__no_default_model_skips(
    db_session: Session,
    collection: CollectionTable,
    samples: list[ImageTable],
    mocker: MockerFixture,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """With no default model, embedding is skipped, a warning logged, nothing stored."""
    _disable_env_loader(mocker)
    sample_ids = [sample.sample_id for sample in samples]

    with caplog.at_level(logging.WARNING):
        embed_samples.embed_image_samples(
            session=db_session, collection_id=collection.collection_id, sample_ids=sample_ids
        )

    assert "No embedding model loaded" in caplog.text
    assert _stored_embeddings(db_session) == []


def test_embed_annotation_collection(
    db_session: Session,
    collection: CollectionTable,
    patched_manager: EmbeddingManager,
) -> None:
    """Annotation crops are embedded and stored under the collection's default model."""
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
    collection: CollectionTable,
    mocker: MockerFixture,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """With no default model, annotation embedding is skipped and nothing stored."""
    annotation_collection_id = collection_resolver.get_or_create_child_collection(
        session=db_session,
        collection_id=collection.collection_id,
        sample_type=SampleType.ANNOTATION,
    )
    _disable_env_loader(mocker)

    with caplog.at_level(logging.WARNING):
        embed_samples.embed_annotation_collection(
            session=db_session, annotation_collection_id=annotation_collection_id
        )

    assert "No embedding model loaded" in caplog.text
    assert _stored_embeddings(db_session) == []


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
