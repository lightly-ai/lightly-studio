from __future__ import annotations

import logging
from uuid import uuid4

import pytest
from lightly_studio_serve.embedder import Embedder
from sqlmodel import Session

from lightly_studio.embed import default_embedder
from lightly_studio.embed.embedder_registry import EmbedderRegistry
from lightly_studio.embed.random_embedder import RandomEmbedder
from lightly_studio.resolvers import (
    collection_embedding_model_resolver,
    embedding_model_resolver,
)
from tests.helpers_resolvers import create_collection, create_embedding_model


class _RecordingSelector:
    """Selector stub that returns a fixed embedder and records the space keys it saw."""

    def __init__(self, embedder: Embedder | None) -> None:
        self._embedder = embedder
        self.space_keys: list[str | None] = []

    def __call__(self, _registry: EmbedderRegistry, space_key: str | None) -> Embedder | None:
        self.space_keys.append(space_key)
        return self._embedder


def test_resolve_default_embedder__uses_existing_default(db_session: Session) -> None:
    collection = create_collection(session=db_session)
    model = create_embedding_model(
        session=db_session,
        collection_id=collection.collection_id,
        embedding_model_name="existing_space",
        set_as_default=True,
    )
    embedder = RandomEmbedder()
    selector = _RecordingSelector(embedder=embedder)

    result = default_embedder.resolve_default_embedder(
        session=db_session,
        collection_id=collection.collection_id,
        select_embedder=selector,
    )

    assert result == (embedder, model.embedding_model_id)
    # The default model's name selects the embedder's space.
    assert selector.space_keys == ["existing_space"]
    # No extra model is registered.
    linked = collection_embedding_model_resolver.get_all_by_collection_id(
        session=db_session, collection_id=collection.collection_id
    )
    assert linked == [model.embedding_model_id]


def test_resolve_default_embedder__registers_bootstrap_when_no_default(db_session: Session) -> None:
    collection = create_collection(session=db_session)
    embedder = RandomEmbedder(dimension=3)
    selector = _RecordingSelector(embedder=embedder)

    result = default_embedder.resolve_default_embedder(
        session=db_session,
        collection_id=collection.collection_id,
        select_embedder=selector,
    )

    assert result is not None
    returned_embedder, model_id = result
    assert returned_embedder is embedder
    # With no default set, the selector is asked for the bootstrap space.
    assert selector.space_keys == [None]
    # The embedder's space is registered and becomes the collection default.
    registered = embedding_model_resolver.get_by_id(session=db_session, embedding_model_id=model_id)
    assert registered is not None
    assert registered.name == "random_model"
    assert registered.embedding_dimension == 3
    assert (
        collection_embedding_model_resolver.get_default_by_collection_id(
            session=db_session, collection_id=collection.collection_id
        )
        == model_id
    )


def test_resolve_default_embedder__none_when_no_embedder(
    db_session: Session, caplog: pytest.LogCaptureFixture
) -> None:
    collection = create_collection(session=db_session)
    selector = _RecordingSelector(embedder=None)

    with caplog.at_level(logging.WARNING):
        result = default_embedder.resolve_default_embedder(
            session=db_session,
            collection_id=collection.collection_id,
            select_embedder=selector,
        )

    assert result is None
    assert "No embedding model loaded" in caplog.text


def test_resolve_default_embedder__missing_collection_raises(db_session: Session) -> None:
    selector = _RecordingSelector(embedder=RandomEmbedder())

    with pytest.raises(ValueError, match=r"could not be found"):
        default_embedder.resolve_default_embedder(
            session=db_session,
            collection_id=uuid4(),
            select_embedder=selector,
        )
