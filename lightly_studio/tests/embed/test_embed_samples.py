"""Tests for the class-free embed_samples interface."""

from __future__ import annotations

from uuid import UUID

import pytest
from pytest_mock import MockerFixture
from sqlmodel import Session, select

from lightly_studio.dataset.embedding_generator import RandomEmbeddingGenerator
from lightly_studio.dataset.embedding_manager import (
    EmbeddingManager,
    EmbeddingManagerProvider,
)
from lightly_studio.embed import embed_samples
from lightly_studio.models.sample_embedding import SampleEmbeddingTable
from tests.helpers_resolvers import create_collection


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


def _stored_embeddings(session: Session) -> list[SampleEmbeddingTable]:
    """Return every stored sample embedding, for asserting the skip path stores nothing."""
    return list(session.exec(select(SampleEmbeddingTable)).all())
