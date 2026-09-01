from __future__ import annotations

import pytest
from sqlmodel import Session

from lightly_studio.models.embedding_model import EmbeddingModelCreate
from lightly_studio.resolvers import (
    collection_embedding_model_resolver,
    embedding_model_resolver,
)
from tests.helpers_resolvers import (
    create_collection,
    create_embedding_model,
)


def test_create_embedding_model(db_session: Session) -> None:
    collection = create_collection(session=db_session)
    collection_id = collection.collection_id
    embedding_model = create_embedding_model(
        session=db_session,
        collection_id=collection_id,
        embedding_model_name="example_embedding_model",
    )
    assert embedding_model.name == "example_embedding_model"


def test_read_embedding_model(db_session: Session) -> None:
    collection = create_collection(session=db_session)
    collection_id = collection.collection_id

    embedding_model = create_embedding_model(session=db_session, collection_id=collection_id)

    embedding_model_from_resolver = embedding_model_resolver.get_by_id(
        session=db_session, embedding_model_id=embedding_model.embedding_model_id
    )
    assert embedding_model_from_resolver is not None
    assert embedding_model_from_resolver.embedding_model_id == embedding_model.embedding_model_id
    assert embedding_model_from_resolver.name == embedding_model.name


def test_get_by_model_hash(db_session: Session) -> None:
    collection = create_collection(session=db_session)
    collection_id = collection.collection_id

    embedding_model_1 = create_embedding_model(
        session=db_session,
        collection_id=collection_id,
        embedding_model_name="embedding_model_1",
        embedding_model_hash="hash_1",
    )
    create_embedding_model(
        session=db_session,
        collection_id=collection_id,
        embedding_model_name="embedding_model_2",
        embedding_model_hash="hash_2",
    )

    embedding_model = embedding_model_resolver.get_by_model_hash(
        session=db_session, embedding_model_hash="hash_1", dataset_id=collection.dataset_id
    )
    assert embedding_model is not None
    assert embedding_model.name == embedding_model_1.name

    embedding_model = embedding_model_resolver.get_by_model_hash(
        session=db_session, embedding_model_hash="hash_3", dataset_id=collection.dataset_id
    )
    assert embedding_model is None


def test_get_by_model_hash__scoped_by_dataset(db_session: Session) -> None:
    # Root collections each get their own dataset, so these models live in different datasets.
    collection_1 = create_collection(session=db_session, collection_name="collection_1")
    collection_2 = create_collection(session=db_session, collection_name="collection_2")

    # Create models with the same hash in different datasets.
    model_1 = create_embedding_model(
        session=db_session,
        collection_id=collection_1.collection_id,
        embedding_model_name="model_in_dataset_1",
        embedding_model_hash="same_hash",
    )
    model_2 = create_embedding_model(
        session=db_session,
        collection_id=collection_2.collection_id,
        embedding_model_name="model_in_dataset_2",
        embedding_model_hash="same_hash",
    )

    # With dataset_id, returns the model owned by that dataset.
    result = embedding_model_resolver.get_by_model_hash(
        session=db_session,
        embedding_model_hash="same_hash",
        dataset_id=collection_1.dataset_id,
    )
    assert result is not None
    assert result.embedding_model_id == model_1.embedding_model_id
    assert result.embedding_model_hash == "same_hash"

    result = embedding_model_resolver.get_by_model_hash(
        session=db_session,
        embedding_model_hash="same_hash",
        dataset_id=collection_2.dataset_id,
    )
    assert result is not None
    assert result.embedding_model_id == model_2.embedding_model_id
    assert result.embedding_model_hash == "same_hash"

    # A dataset without a matching model returns None.
    collection_3 = create_collection(session=db_session, collection_name="collection_3")
    result_3 = embedding_model_resolver.get_by_model_hash(
        session=db_session,
        embedding_model_hash="same_hash",
        dataset_id=collection_3.dataset_id,
    )
    assert result_3 is None


def test_get_or_create__creates_new_model(db_session: Session) -> None:
    """get_or_create should insert a model when none exists for the hash."""
    collection = create_collection(session=db_session)

    model_create = EmbeddingModelCreate(
        dataset_id=collection.dataset_id,
        name="Model Name",
        embedding_model_hash="model_hash",
        embedding_dimension=768,
    )
    created = embedding_model_resolver.get_or_create(
        session=db_session, embedding_model=model_create
    )

    assert created.embedding_model_hash == "model_hash"
    assert created.name == "Model Name"
    assert created.embedding_dimension == 768
    assert created.dataset_id == collection.dataset_id


def test_get_or_create__reuses_existing_model(db_session: Session) -> None:
    """get_or_create should return the existing model for a matching hash."""
    collection = create_collection(session=db_session)
    existing = create_embedding_model(
        session=db_session,
        collection_id=collection.collection_id,
        embedding_model_name="Model Name",
        embedding_model_hash="model_hash",
        embedding_dimension=32,
    )

    model_create = EmbeddingModelCreate(
        dataset_id=collection.dataset_id,
        name="Model Name",
        embedding_model_hash="model_hash",
        embedding_dimension=32,
    )

    reused = embedding_model_resolver.get_or_create(
        session=db_session, embedding_model=model_create
    )

    assert reused.embedding_model_id == existing.embedding_model_id
    model_ids = collection_embedding_model_resolver.get_all_by_collection_id(
        session=db_session, collection_id=collection.collection_id
    )
    assert len(model_ids) == 1


def test_get_or_create__conflicting_model_raises(db_session: Session) -> None:
    """Conflicting metadata for the same hash should raise an error."""
    collection = create_collection(session=db_session)
    create_embedding_model(
        session=db_session,
        collection_id=collection.collection_id,
        embedding_model_name="Model Name",
        embedding_model_hash="model_hash",
        embedding_dimension=32,
    )

    conflicting_model_create = EmbeddingModelCreate(
        dataset_id=collection.dataset_id,
        name="Model Name",
        embedding_model_hash="model_hash",
        embedding_dimension=64,
    )

    with pytest.raises(
        ValueError,
        match=r"An embedding model with the same hash but different parameters already exists.",
    ):
        embedding_model_resolver.get_or_create(
            session=db_session, embedding_model=conflicting_model_create
        )


def test_get_or_create__same_hash_different_datasets(db_session: Session) -> None:
    # Root collections each get their own dataset, so these models live in different datasets.
    collection_1 = create_collection(session=db_session, collection_name="collection_1")
    collection_2 = create_collection(session=db_session, collection_name="collection_2")

    model_create_1 = EmbeddingModelCreate(
        dataset_id=collection_1.dataset_id,
        name="Test Model",
        embedding_model_hash="same_hash",
        embedding_dimension=32,
    )
    model_1 = embedding_model_resolver.get_or_create(
        session=db_session, embedding_model=model_create_1
    )

    model_create_2 = EmbeddingModelCreate(
        dataset_id=collection_2.dataset_id,
        name="Test Model",
        embedding_model_hash="same_hash",
        embedding_dimension=32,
    )
    model_2 = embedding_model_resolver.get_or_create(
        session=db_session, embedding_model=model_create_2
    )

    # Should be different models
    assert model_1.embedding_model_id != model_2.embedding_model_id
    assert model_1.dataset_id == collection_1.dataset_id
    assert model_2.dataset_id == collection_2.dataset_id

    # Each dataset resolves the shared hash to its own model, so the two are not merged.
    model_1_by_hash = embedding_model_resolver.get_by_model_hash(
        session=db_session,
        dataset_id=collection_1.dataset_id,
        embedding_model_hash="same_hash",
    )
    model_2_by_hash = embedding_model_resolver.get_by_model_hash(
        session=db_session,
        dataset_id=collection_2.dataset_id,
        embedding_model_hash="same_hash",
    )
    assert model_1_by_hash is not None
    assert model_2_by_hash is not None
    assert model_1_by_hash.embedding_model_id == model_1.embedding_model_id
    assert model_2_by_hash.embedding_model_id == model_2.embedding_model_id
