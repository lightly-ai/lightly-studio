"""Tests for the class-free embed_samples interface."""

from __future__ import annotations

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
from lightly_studio.models.collection import CollectionTable
from lightly_studio.models.sample_embedding import SampleEmbeddingTable

# Dimension of the RandomEmbeddingGenerator registered as the default in these tests.
_MODEL_DIMENSION = 3


def test_embed_image_for_collection(
    db_session: Session,
    collection: CollectionTable,
    mocker: MockerFixture,
) -> None:
    """A single image is embedded with the collection's default model, unstored."""
    manager = _fresh_manager(mocker)
    _register_default(manager=manager, session=db_session, collection_id=collection.collection_id)

    embedding = embed_samples.embed_image_for_collection(
        collection_id=collection.collection_id, filepath="/path/to/image.jpg"
    )

    assert len(embedding) == _MODEL_DIMENSION
    # Nothing is stored for an interactive query embedding.
    assert _stored_embeddings(db_session) == []


def test_embed_image_for_collection__no_default_model(
    collection: CollectionTable,
    mocker: MockerFixture,
) -> None:
    """Without a default model the interactive image path raises a clear error."""
    _fresh_manager(mocker)

    with pytest.raises(ValueError, match="No embedding_model_id provided and no default embedding"):
        embed_samples.embed_image_for_collection(
            collection_id=collection.collection_id, filepath="/path/to/image.jpg"
        )


def test_embed_text_for_collection(
    db_session: Session,
    collection: CollectionTable,
    mocker: MockerFixture,
) -> None:
    """A text query is embedded with the collection's default model."""
    manager = _fresh_manager(mocker)
    _register_default(manager=manager, session=db_session, collection_id=collection.collection_id)

    embedding = embed_samples.embed_text_for_collection(
        collection_id=collection.collection_id, text="a red car"
    )

    assert len(embedding) == _MODEL_DIMENSION


def test_embed_text_for_collection__no_default_model(
    collection: CollectionTable,
    mocker: MockerFixture,
) -> None:
    """Without a default model the interactive text path raises a clear error."""
    _fresh_manager(mocker)

    with pytest.raises(ValueError, match="No embedding_model_id provided and no default embedding"):
        embed_samples.embed_text_for_collection(
            collection_id=collection.collection_id, text="a red car"
        )


def _fresh_manager(mocker: MockerFixture) -> EmbeddingManager:
    """Route embed_samples to a fresh manager so tests never touch the shared singleton."""
    manager = EmbeddingManager()
    mocker.patch.object(EmbeddingManagerProvider, "get_embedding_manager", return_value=manager)
    return manager


def _disable_env_loader(mocker: MockerFixture) -> None:
    """Make loading a default generator from the environment return nothing."""
    mocker.patch.object(embedding_manager, "_load_embedding_generator_from_env", return_value=None)


def _register_default(
    manager: EmbeddingManager,
    session: Session,
    collection_id: UUID,
    generator: RandomEmbeddingGenerator | None = None,
) -> UUID:
    """Register an embedding generator as the collection's default and return its model ID."""
    return manager.register_embedding_model(
        session=session,
        embedding_generator=generator or RandomEmbeddingGenerator(dimension=_MODEL_DIMENSION),
        collection_id=collection_id,
        set_as_default=True,
    ).embedding_model_id


def _stored_embeddings(session: Session) -> list[SampleEmbeddingTable]:
    """Return every stored sample embedding, for asserting the skip path stores nothing."""
    return list(session.exec(select(SampleEmbeddingTable)).all())
