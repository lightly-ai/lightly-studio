from __future__ import annotations

import pytest
from pytest_mock import MockerFixture
from sqlmodel import Session

from lightly_studio.embed import default_embedder, embedder_registry
from lightly_studio.embed.embedder_registry import EmbedderRegistry
from lightly_studio.embed.random_embedder import RandomEmbedder
from lightly_studio.resolvers import collection_embedding_model_resolver
from tests.helpers_resolvers import create_collection, create_embedding_model


def test_check_embedder_dimension__mismatch_raises(
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
        default_embedder.check_embedder_dimension(
            session=db_session,
            collection_id=collection.collection_id,
            get_embedder_fn=EmbedderRegistry.get_image_path_embedder,
        )


def test_check_embedder_dimension__no_default_model(
    db_session: Session, mocker: MockerFixture
) -> None:
    collection = create_collection(session=db_session)
    registry = EmbedderRegistry()
    registry.register(embedder=RandomEmbedder(dimension=3))
    mocker.patch.object(embedder_registry, "get_registry", return_value=registry)

    default_embedder.check_embedder_dimension(
        session=db_session,
        collection_id=collection.collection_id,
        get_embedder_fn=EmbedderRegistry.get_image_path_embedder,
    )

    # The check never bootstraps a default model.
    linked = collection_embedding_model_resolver.get_all_by_collection_id(
        session=db_session, collection_id=collection.collection_id
    )
    assert linked == []
