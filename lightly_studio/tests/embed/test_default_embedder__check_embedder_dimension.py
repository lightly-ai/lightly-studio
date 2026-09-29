from __future__ import annotations

import pytest
from pytest_mock import MockerFixture
from sqlmodel import Session

from lightly_studio.embed import default_embedder, embedder_registry
from lightly_studio.embed.embedder_registry import EmbedderRegistry
from lightly_studio.embed.random_embedder import RandomEmbedder
from lightly_studio.resolvers import collection_embedding_model_resolver
from tests.helpers_resolvers import create_collection, create_embedding_model


def test_check_embedder_dimension__default_model_mismatch_raises(
    db_session: Session, mocker: MockerFixture
) -> None:
    _patch_registry(mocker=mocker, embedder=RandomEmbedder(dimension=3))
    collection = create_collection(session=db_session)
    create_embedding_model(
        session=db_session,
        collection_id=collection.collection_id,
        embedding_model_name="random_model",
        embedding_dimension=4,
        set_as_default=True,
    )

    with pytest.raises(ValueError, match=r"does not match"):
        default_embedder.check_embedder_dimension(
            session=db_session,
            collection_id=collection.collection_id,
            get_embedder_fn=EmbedderRegistry.get_image_path_embedder,
        )


def test_check_embedder_dimension__bootstrap_mismatch_raises(
    db_session: Session, mocker: MockerFixture
) -> None:
    _patch_registry(mocker=mocker, embedder=RandomEmbedder(dimension=3))
    collection = create_collection(session=db_session)
    # The dataset holds the bootstrap space, and the collection has no default model.
    create_embedding_model(
        session=db_session,
        collection_id=collection.collection_id,
        embedding_model_name="random_model",
        embedding_dimension=4,
    )

    with pytest.raises(ValueError, match=r"does not match"):
        default_embedder.check_embedder_dimension(
            session=db_session,
            collection_id=collection.collection_id,
            get_embedder_fn=EmbedderRegistry.get_image_path_embedder,
        )


def test_check_embedder_dimension__bootstrap_matches(
    db_session: Session, mocker: MockerFixture
) -> None:
    _patch_registry(mocker=mocker, embedder=RandomEmbedder(dimension=3))
    collection = create_collection(session=db_session)
    create_embedding_model(
        session=db_session,
        collection_id=collection.collection_id,
        embedding_model_name="random_model",
        embedding_dimension=3,
    )

    default_embedder.check_embedder_dimension(
        session=db_session,
        collection_id=collection.collection_id,
        get_embedder_fn=EmbedderRegistry.get_image_path_embedder,
    )

    # The check never registers a default model.
    assert (
        collection_embedding_model_resolver.get_default_by_collection_id(
            session=db_session, collection_id=collection.collection_id
        )
        is None
    )


def test_check_embedder_dimension__dataset_without_models(
    db_session: Session, mocker: MockerFixture
) -> None:
    collection = create_collection(session=db_session)
    get_embedder_fn = mocker.MagicMock()

    default_embedder.check_embedder_dimension(
        session=db_session,
        collection_id=collection.collection_id,
        get_embedder_fn=get_embedder_fn,
    )

    # A first import loads no embedder before its samples are stored.
    get_embedder_fn.assert_not_called()
    linked = collection_embedding_model_resolver.get_all_by_collection_id(
        session=db_session, collection_id=collection.collection_id
    )
    assert linked == []


def _patch_registry(mocker: MockerFixture, embedder: RandomEmbedder) -> None:
    """Replace the process-wide registry with one that holds only ``embedder``."""
    registry = EmbedderRegistry()
    registry.register(embedder=embedder)
    mocker.patch.object(embedder_registry, "get_registry", return_value=registry)
