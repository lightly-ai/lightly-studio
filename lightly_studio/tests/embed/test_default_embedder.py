from __future__ import annotations

import logging
import uuid

import pytest
from pytest_mock import MockerFixture
from sqlmodel import Session

from lightly_studio.embed import default_embedder, embedder_registry
from lightly_studio.embed.embedder_registry import EmbedderRegistry
from lightly_studio.embed.random_embedder import RandomEmbedder
from lightly_studio.resolvers import (
    collection_embedding_model_resolver,
    embedding_model_resolver,
)
from tests.helpers_resolvers import create_collection, create_embedding_model


def test_resolve_default_embedder__uses_existing_default(
    db_session: Session, mocker: MockerFixture
) -> None:
    collection = create_collection(session=db_session)
    embedder = RandomEmbedder(dimension=3)
    registry = EmbedderRegistry()
    registry.register(embedder=embedder)
    mocker.patch.object(embedder_registry, "get_registry", return_value=registry)
    # The default model's name matches the registered embedder's space, so it is selected.
    model = create_embedding_model(
        session=db_session,
        collection_id=collection.collection_id,
        embedding_model_name="random_model",
        embedding_dimension=3,
        set_as_default=True,
    )

    result = default_embedder.resolve_default_embedder(
        session=db_session,
        collection_id=collection.collection_id,
        get_embedder_fn=EmbedderRegistry.get_image_path_embedder,
    )

    assert result == (embedder, model.embedding_model_id)
    # No extra model is registered.
    linked = collection_embedding_model_resolver.get_all_by_collection_id(
        session=db_session, collection_id=collection.collection_id
    )
    assert linked == [model.embedding_model_id]


def test_resolve_default_embedder__registers_bootstrap_when_no_default(
    db_session: Session, mocker: MockerFixture
) -> None:
    collection = create_collection(session=db_session)
    embedder = RandomEmbedder(dimension=3)
    registry = EmbedderRegistry()
    registry.register(embedder=embedder)
    mocker.patch.object(embedder_registry, "get_registry", return_value=registry)

    result = default_embedder.resolve_default_embedder(
        session=db_session,
        collection_id=collection.collection_id,
        get_embedder_fn=EmbedderRegistry.get_image_path_embedder,
    )

    assert result is not None
    returned_embedder, model_id = result
    assert returned_embedder is embedder
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


def test_resolve_default_embedder__default_dimension_mismatch_raises(
    db_session: Session, mocker: MockerFixture
) -> None:
    collection = create_collection(session=db_session)
    # The embedder shares the space but produces a different dimension.
    registry = EmbedderRegistry()
    registry.register(embedder=RandomEmbedder(dimension=3))
    mocker.patch.object(embedder_registry, "get_registry", return_value=registry)
    create_embedding_model(
        session=db_session,
        collection_id=collection.collection_id,
        embedding_model_name="random_model",
        embedding_dimension=8,
        set_as_default=True,
    )

    with pytest.raises(ValueError, match=r"does not match"):
        default_embedder.resolve_default_embedder(
            session=db_session,
            collection_id=collection.collection_id,
            get_embedder_fn=EmbedderRegistry.get_image_path_embedder,
        )


def test_resolve_default_embedder__bootstrap_dimension_mismatch_raises(
    db_session: Session, mocker: MockerFixture
) -> None:
    collection = create_collection(session=db_session)
    registry = EmbedderRegistry()
    registry.register(embedder=RandomEmbedder(dimension=3))
    mocker.patch.object(embedder_registry, "get_registry", return_value=registry)
    # The dataset already has the bootstrap space registered with a different dimension, but the
    # collection has no default: a wrongly registered embedder.
    create_embedding_model(
        session=db_session,
        collection_id=collection.collection_id,
        embedding_model_name="random_model",
        embedding_dimension=8,
        set_as_default=False,
    )

    with pytest.raises(ValueError, match=r"different parameters"):
        default_embedder.resolve_default_embedder(
            session=db_session,
            collection_id=collection.collection_id,
            get_embedder_fn=EmbedderRegistry.get_image_path_embedder,
        )


def test_resolve_default_embedder__none_when_no_embedder(
    db_session: Session, mocker: MockerFixture, caplog: pytest.LogCaptureFixture
) -> None:
    collection = create_collection(session=db_session)
    # The registry has no embedder for the requested capability.
    registry = EmbedderRegistry()
    mocker.patch.object(embedder_registry, "get_registry", return_value=registry)

    with caplog.at_level(logging.WARNING):
        result = default_embedder.resolve_default_embedder(
            session=db_session,
            collection_id=collection.collection_id,
            get_embedder_fn=EmbedderRegistry.get_text_embedder,
        )

    assert result is None
    assert "No embedding model loaded" in caplog.text


def test_resolve_default_embedder__missing_collection_raises(
    db_session: Session, mocker: MockerFixture
) -> None:
    registry = EmbedderRegistry()
    registry.register(embedder=RandomEmbedder())
    mocker.patch.object(embedder_registry, "get_registry", return_value=registry)

    with pytest.raises(ValueError, match=r"could not be found"):
        default_embedder.resolve_default_embedder(
            session=db_session,
            collection_id=uuid.uuid4(),
            get_embedder_fn=EmbedderRegistry.get_image_path_embedder,
        )
