from __future__ import annotations

import pytest
from lightly_studio_serve.embedder import Embedder, ImagePathEmbedder
from lightly_studio_serve.types import EmbeddingResult, EmbeddingSpaceSpec
from pytest_mock import MockerFixture
from sqlmodel import Session

from lightly_studio.embed import default_embedder, embedder_registry
from lightly_studio.embed.embedder_registry import EmbedderRegistry
from lightly_studio.embed.random_embedder import RandomEmbedder
from lightly_studio.embed.remote.endpoint import RemoteEndpoint
from lightly_studio.resolvers import embedding_model_resolver
from tests.helpers_resolvers import create_collection, create_embedding_model


class _EndpointImageEmbedder(ImagePathEmbedder):
    """Names the server that it calls, the way a remote embedder does, and is no such one."""

    def __init__(self, endpoint: RemoteEndpoint | None) -> None:
        self._endpoint = endpoint

    def embedding_space_spec(self) -> EmbeddingSpaceSpec:
        return EmbeddingSpaceSpec(space_key="acme/model@v1", dimension=2)

    def embed_images(self, paths: list[str]) -> EmbeddingResult:
        raise NotImplementedError

    def remote_endpoint(self) -> RemoteEndpoint | None:
        return self._endpoint


def test_resolve_default_embedder__stores_remote_endpoint(
    db_session: Session, mocker: MockerFixture
) -> None:
    collection = create_collection(session=db_session)
    registry = EmbedderRegistry()
    registry.register(
        embedder=_EndpointImageEmbedder(
            endpoint=RemoteEndpoint(url="http://embedder.test", api_key="secret-token")
        )
    )
    mocker.patch.object(embedder_registry, "get_registry", return_value=registry)

    result = default_embedder.resolve_default_embedder(
        session=db_session,
        collection_id=collection.collection_id,
        embedder_type=ImagePathEmbedder,
    )

    assert result is not None
    stored = embedding_model_resolver.get_by_id(session=db_session, embedding_model_id=result[1])
    assert stored is not None
    assert stored.remote_embedder_url == "http://embedder.test"
    assert stored.api_key == "secret-token"


@pytest.mark.parametrize(
    "embedder",
    [RandomEmbedder(dimension=3), _EndpointImageEmbedder(endpoint=None)],
    ids=["local", "no_endpoint"],
)
def test_resolve_default_embedder__stores_no_server(
    db_session: Session, mocker: MockerFixture, embedder: Embedder
) -> None:
    collection = create_collection(session=db_session)
    registry = EmbedderRegistry()
    registry.register(embedder=embedder)
    mocker.patch.object(embedder_registry, "get_registry", return_value=registry)

    result = default_embedder.resolve_default_embedder(
        session=db_session,
        collection_id=collection.collection_id,
        embedder_type=ImagePathEmbedder,
    )

    assert result is not None
    stored = embedding_model_resolver.get_by_id(session=db_session, embedding_model_id=result[1])
    assert stored is not None
    assert stored.remote_embedder_url is None
    assert stored.api_key is None


def test_resolve_default_embedder__local_embedder_keeps_stored_server(
    db_session: Session, mocker: MockerFixture
) -> None:
    collection = create_collection(session=db_session)
    registry = EmbedderRegistry()
    registry.register(embedder=RandomEmbedder(dimension=3))
    mocker.patch.object(embedder_registry, "get_registry", return_value=registry)
    # The dataset already stores a server for the space, and the collection has no default.
    model = create_embedding_model(
        session=db_session,
        collection_id=collection.collection_id,
        embedding_model_name="random_model",
        embedding_dimension=3,
    )
    embedding_model_resolver.set_remote_embedder(
        session=db_session,
        embedding_model_id=model.embedding_model_id,
        url="http://embedder.test",
        api_key="secret-token",
    )

    default_embedder.resolve_default_embedder(
        session=db_session,
        collection_id=collection.collection_id,
        embedder_type=ImagePathEmbedder,
    )

    stored = embedding_model_resolver.get_by_id(
        session=db_session, embedding_model_id=model.embedding_model_id
    )
    assert stored is not None
    assert stored.remote_embedder_url == "http://embedder.test"
    assert stored.api_key == "secret-token"


def test_resolve_default_embedder__keeps_stored_server(
    db_session: Session, mocker: MockerFixture
) -> None:
    collection = create_collection(session=db_session)
    registry = EmbedderRegistry()
    registry.register(
        embedder=_EndpointImageEmbedder(
            endpoint=RemoteEndpoint(url="http://other.test", api_key="other-token")
        )
    )
    mocker.patch.object(embedder_registry, "get_registry", return_value=registry)
    # The dataset already stores a server for the space, and the collection has no default.
    model = create_embedding_model(
        session=db_session,
        collection_id=collection.collection_id,
        embedding_model_name="acme/model@v1",
        embedding_dimension=2,
    )
    embedding_model_resolver.set_remote_embedder(
        session=db_session,
        embedding_model_id=model.embedding_model_id,
        url="http://embedder.test",
        api_key="secret-token",
    )

    default_embedder.resolve_default_embedder(
        session=db_session,
        collection_id=collection.collection_id,
        embedder_type=ImagePathEmbedder,
    )

    stored = embedding_model_resolver.get_by_id(
        session=db_session, embedding_model_id=model.embedding_model_id
    )
    assert stored is not None
    assert stored.remote_embedder_url == "http://embedder.test"
    assert stored.api_key == "secret-token"
