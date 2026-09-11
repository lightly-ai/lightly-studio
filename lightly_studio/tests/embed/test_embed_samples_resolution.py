"""Tests for collection default resolution in embed_samples."""

from __future__ import annotations

import numpy as np
import pytest
from lightly_studio_serve.embedder import Capability, ImagePathEmbedder
from lightly_studio_serve.types import EmbeddingResult, EmbeddingSpaceSpec
from pytest_mock import MockerFixture
from sqlmodel import Session

from lightly_studio.embed import embed_samples, embedder_registry
from lightly_studio.embed.embedder_registry import EmbedderRegistry
from lightly_studio.models.embedding_model import EmbeddingModelCreate
from lightly_studio.resolvers import (
    collection_embedding_model_resolver,
    embedding_model_resolver,
)
from tests.helpers_resolvers import create_collection, create_embedding_model


class _FakeImageEmbedder(ImagePathEmbedder):
    def __init__(self, space_key: str, dimension: int) -> None:
        self._spec = EmbeddingSpaceSpec(space_key=space_key, dimension=dimension)

    def embedding_space_spec(self) -> EmbeddingSpaceSpec:
        return self._spec

    def embed_images(self, paths: list[str]) -> EmbeddingResult:
        return EmbeddingResult(
            embeddings=np.zeros((len(paths), self._spec.dimension), dtype=np.float32),
            kept_indices=list(range(len(paths))),
        )


@pytest.fixture
def registry(mocker: MockerFixture) -> EmbedderRegistry:
    registry = EmbedderRegistry()
    mocker.patch.object(embedder_registry, "_registry", registry)
    return registry


def test_resolve_for_embedding__persists_bootstrap_default(
    db_session: Session,
    registry: EmbedderRegistry,
) -> None:
    collection = create_collection(session=db_session)
    embedder = _FakeImageEmbedder(space_key="custom", dimension=5)
    registry.register(embedder=embedder)

    resolved = embed_samples._resolve_for_embedding(
        session=db_session,
        collection_id=collection.collection_id,
        get_embedder=registry.get_image_path_embedder,
    )

    assert resolved is not None
    assert resolved[0] is embedder
    model = embed_samples._get_default_model(
        session=db_session, collection_id=collection.collection_id
    )
    assert model is not None
    assert resolved[1] == model.embedding_model_id
    assert model.name == "custom"
    assert model.embedding_dimension == 5


def test_resolve_for_embedding__preserves_existing_default(
    db_session: Session,
    registry: EmbedderRegistry,
) -> None:
    collection = create_collection(session=db_session)
    model = create_embedding_model(
        session=db_session,
        collection_id=collection.collection_id,
        embedding_model_name="persisted",
        embedding_dimension=2,
        set_as_default=True,
    )
    persisted = _FakeImageEmbedder(space_key="persisted", dimension=2)
    registry.register(embedder=persisted, bootstrap_for=set())
    registry.register(embedder=_FakeImageEmbedder(space_key="new-bootstrap", dimension=3))

    resolved = embed_samples._resolve_for_embedding(
        session=db_session,
        collection_id=collection.collection_id,
        get_embedder=registry.get_image_path_embedder,
    )

    assert resolved == (persisted, model.embedding_model_id)
    assert (
        collection_embedding_model_resolver.get_default_by_collection_id(
            session=db_session, collection_id=collection.collection_id
        )
        == model.embedding_model_id
    )


@pytest.mark.parametrize("space_key", ["mobileclip_s0", "PE-Core-T16-384"])
def test_resolve_for_embedding__reloads_persisted_builtin_by_key(
    db_session: Session,
    registry: EmbedderRegistry,
    mocker: MockerFixture,
    space_key: str,
) -> None:
    collection = create_collection(session=db_session)
    model = create_embedding_model(
        session=db_session,
        collection_id=collection.collection_id,
        embedding_model_name=space_key,
        embedding_dimension=2,
        set_as_default=True,
    )
    persisted = _FakeImageEmbedder(space_key=space_key, dimension=2)
    load_builtin = mocker.patch.object(
        embedder_registry, "_load_builtin_embedder", return_value=persisted
    )

    resolved = embed_samples._resolve_for_embedding(
        session=db_session,
        collection_id=collection.collection_id,
        get_embedder=registry.get_image_path_embedder,
    )

    assert resolved == (persisted, model.embedding_model_id)
    load_builtin.assert_called_once_with(space_key=space_key)


def test_resolve_for_embedding__custom_default_requires_reregistration(
    db_session: Session,
    registry: EmbedderRegistry,
    mocker: MockerFixture,
) -> None:
    collection = create_collection(session=db_session)
    model = create_embedding_model(
        session=db_session,
        collection_id=collection.collection_id,
        embedding_model_name="custom",
        embedding_dimension=2,
        set_as_default=True,
    )
    mocker.patch.object(embedder_registry, "_load_builtin_embedder", return_value=None)

    unavailable = embed_samples._resolve_for_embedding(
        session=db_session,
        collection_id=collection.collection_id,
        get_embedder=registry.get_image_path_embedder,
    )
    custom = _FakeImageEmbedder(space_key="custom", dimension=2)
    registry.register(embedder=custom, bootstrap_for=set())
    available = embed_samples._resolve_for_embedding(
        session=db_session,
        collection_id=collection.collection_id,
        get_embedder=registry.get_image_path_embedder,
    )

    assert unavailable is None
    assert available == (custom, model.embedding_model_id)


def test_resolve_for_embedding__rejects_runtime_dimension_conflict(
    db_session: Session,
    registry: EmbedderRegistry,
) -> None:
    collection = create_collection(session=db_session)
    create_embedding_model(
        session=db_session,
        collection_id=collection.collection_id,
        embedding_model_name="custom",
        embedding_dimension=2,
        set_as_default=True,
    )
    registry.register(
        embedder=_FakeImageEmbedder(space_key="custom", dimension=3), bootstrap_for=set()
    )

    with pytest.raises(ValueError, match="does not match persisted model"):
        embed_samples._resolve_for_embedding(
            session=db_session,
            collection_id=collection.collection_id,
            get_embedder=registry.get_image_path_embedder,
        )


def test_resolve_query_embedder__rejects_runtime_dimension_conflict(
    db_session: Session,
    registry: EmbedderRegistry,
) -> None:
    collection = create_collection(session=db_session)
    create_embedding_model(
        session=db_session,
        collection_id=collection.collection_id,
        embedding_model_name="custom",
        embedding_dimension=2,
        set_as_default=True,
    )
    registry.register(
        embedder=_FakeImageEmbedder(space_key="custom", dimension=3), bootstrap_for=set()
    )

    with pytest.raises(ValueError, match="does not match persisted model"):
        embed_samples._resolve_query_embedder(
            session=db_session,
            collection_id=collection.collection_id,
            capability=Capability.IMAGE_PATH,
            get_embedder=registry.get_image_path_embedder,
        )


def test_resolve_query_embedder__does_not_create_default(
    db_session: Session,
    registry: EmbedderRegistry,
) -> None:
    collection = create_collection(session=db_session)
    registry.register(embedder=_FakeImageEmbedder(space_key="custom", dimension=2))

    with pytest.raises(ValueError, match="has no default embedding model"):
        embed_samples._resolve_query_embedder(
            session=db_session,
            collection_id=collection.collection_id,
            capability=Capability.IMAGE_PATH,
            get_embedder=registry.get_image_path_embedder,
        )

    assert (
        collection_embedding_model_resolver.get_default_by_collection_id(
            session=db_session, collection_id=collection.collection_id
        )
        is None
    )


def test_resolve_for_embedding__rejects_dataset_model_dimension_conflict(
    db_session: Session,
    registry: EmbedderRegistry,
) -> None:
    collection = create_collection(session=db_session)
    embedding_model_resolver.create(
        session=db_session,
        embedding_model=EmbeddingModelCreate(
            name="custom",
            embedding_dimension=2,
            dataset_id=collection.dataset_id,
        ),
    )
    registry.register(embedder=_FakeImageEmbedder(space_key="custom", dimension=3))

    with pytest.raises(ValueError, match="same name but different parameters"):
        embed_samples._resolve_for_embedding(
            session=db_session,
            collection_id=collection.collection_id,
            get_embedder=registry.get_image_path_embedder,
        )
