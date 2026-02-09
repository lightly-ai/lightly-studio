from __future__ import annotations

import pytest
from sqlmodel import Session

from lightly_studio.models.embedding_model import EmbeddingModelCreate
from lightly_studio.resolvers import embedding_model_resolver
from tests.helpers_resolvers import (
    create_collection,
    create_embedding_model,
)


def test_create_embedding_model(test_db: Session) -> None:
    collection = create_collection(session=test_db)
    collection_id = collection.collection_id
    embedding_model = create_embedding_model(
        session=test_db,
        collection_id=collection_id,
        embedding_model_name="example_embedding_model",
    )
    assert embedding_model.name == "example_embedding_model"


def test_read_embedding_models(test_db: Session) -> None:
    collection = create_collection(session=test_db)
    collection_id = collection.collection_id

    embedding_model_1 = create_embedding_model(
        session=test_db,
        collection_id=collection_id,
        embedding_model_name="embedding_model_1",
    )
    embedding_model_2 = create_embedding_model(
        session=test_db,
        collection_id=collection_id,
        embedding_model_name="embedding_model_2",
    )

    # Get all embedding models of a collection.
    embedding_models = embedding_model_resolver.get_all_by_collection_id(
        session=test_db, collection_id=collection_id
    )
    assert len(embedding_models) == 2

    assert embedding_models[0].embedding_model_id == embedding_model_1.embedding_model_id
    assert embedding_models[1].embedding_model_id == embedding_model_2.embedding_model_id


def test_read_embedding_model(test_db: Session) -> None:
    collection = create_collection(session=test_db)
    collection_id = collection.collection_id

    embedding_model = create_embedding_model(session=test_db, collection_id=collection_id)

    embedding_model_from_resolver = embedding_model_resolver.get_by_id(
        session=test_db, embedding_model_id=embedding_model.embedding_model_id
    )
    assert embedding_model_from_resolver is not None
    assert embedding_model_from_resolver.embedding_model_id == embedding_model.embedding_model_id
    assert embedding_model_from_resolver.name == embedding_model.name


def test_delete_embedding_model(test_db: Session) -> None:
    collection = create_collection(session=test_db)
    collection_id = collection.collection_id

    embedding_model = create_embedding_model(session=test_db, collection_id=collection_id)

    # Delete the embedding model.
    embedding_model_resolver.delete(
        session=test_db, embedding_model_id=embedding_model.embedding_model_id
    )

    # Assert the embedding model was deleted.
    embedding_model_deleted = embedding_model_resolver.get_by_id(
        session=test_db, embedding_model_id=embedding_model.embedding_model_id
    )
    assert embedding_model_deleted is None


def test_get_by_model_hash(test_db: Session) -> None:
    collection = create_collection(session=test_db)
    collection_id = collection.collection_id

    embedding_model_1 = create_embedding_model(
        session=test_db,
        collection_id=collection_id,
        embedding_model_name="embedding_model_1",
        embedding_model_hash="hash_1",
    )
    create_embedding_model(
        session=test_db,
        collection_id=collection_id,
        embedding_model_name="embedding_model_2",
        embedding_model_hash="hash_2",
    )

    embedding_model = embedding_model_resolver.get_by_model_hash(
        session=test_db, embedding_model_hash="hash_1"
    )
    assert embedding_model is not None
    assert embedding_model.name == embedding_model_1.name

    embedding_model = embedding_model_resolver.get_by_model_hash(
        session=test_db, embedding_model_hash="hash_3"
    )
    assert embedding_model is None


def test_get_by_model_hash__with_collection_id(test_db: Session) -> None:
    collection_1 = create_collection(session=test_db, collection_name="collection_1")
    collection_2 = create_collection(session=test_db, collection_name="collection_2")

    # Create models with same hash in different collections
    model_1 = create_embedding_model(
        session=test_db,
        collection_id=collection_1.collection_id,
        embedding_model_name="model_in_collection_1",
        embedding_model_hash="same_hash",
    )
    model_2 = create_embedding_model(
        session=test_db,
        collection_id=collection_2.collection_id,
        embedding_model_name="model_in_collection_2",
        embedding_model_hash="same_hash",
    )

    # Without collection_id, returns first match
    result = embedding_model_resolver.get_by_model_hash(
        session=test_db, embedding_model_hash="same_hash"
    )
    assert result is not None
    assert result.embedding_model_hash == "same_hash"
    assert result.embedding_model_id == model_1.embedding_model_id
    assert result.collection_id == collection_1.collection_id

    # With collection_id, returns the correct model
    result = embedding_model_resolver.get_by_model_hash(
        session=test_db,
        embedding_model_hash="same_hash",
        collection_id=collection_1.collection_id,
    )
    assert result is not None
    assert result.embedding_model_id == model_1.embedding_model_id
    assert result.embedding_model_hash == "same_hash"
    assert result.collection_id == collection_1.collection_id

    result = embedding_model_resolver.get_by_model_hash(
        session=test_db,
        embedding_model_hash="same_hash",
        collection_id=collection_2.collection_id,
    )
    assert result is not None
    assert result.embedding_model_id == model_2.embedding_model_id
    assert result.embedding_model_hash == "same_hash"
    assert result.collection_id == collection_2.collection_id

    # With non-matching collection_id, returns None
    collection_3 = create_collection(session=test_db, collection_name="collection_3")
    result_3 = embedding_model_resolver.get_by_model_hash(
        session=test_db,
        embedding_model_hash="same_hash",
        collection_id=collection_3.collection_id,
    )
    assert result_3 is None


def test_get_by_name__none_with_single_model(test_db: Session) -> None:
    """Test get_by_name when embedding_model_name is None and exactly one model exists."""
    collection = create_collection(session=test_db)
    collection_id = collection.collection_id

    embedding_model = create_embedding_model(
        session=test_db,
        collection_id=collection_id,
        embedding_model_name="embedding_model_1",
    )

    result = embedding_model_resolver.get_by_name(
        session=test_db, collection_id=collection_id, embedding_model_name=None
    )
    assert result.embedding_model_id == embedding_model.embedding_model_id
    assert result.name == "embedding_model_1"


def test_get_by_name__none_with_multiple_models(test_db: Session) -> None:
    """Test get_by_name when embedding_model_name is None but multiple models exist."""
    collection = create_collection(session=test_db)
    collection_id = collection.collection_id

    create_embedding_model(
        session=test_db,
        collection_id=collection_id,
        embedding_model_name="embedding_model_1",
    )
    create_embedding_model(
        session=test_db,
        collection_id=collection_id,
        embedding_model_name="embedding_model_2",
    )

    with pytest.raises(
        ValueError,
        match=r"Expected exactly one embedding model, but found 2 with names "
        r"\['embedding_model_1', 'embedding_model_2'\]\.",
    ):
        embedding_model_resolver.get_by_name(
            session=test_db, collection_id=collection_id, embedding_model_name=None
        )


def test_get_by_name__none_with_no_models(test_db: Session) -> None:
    """Test get_by_name when embedding_model_name is None but no models exist."""
    collection = create_collection(session=test_db)
    collection_id = collection.collection_id

    with pytest.raises(
        ValueError, match=r"Expected exactly one embedding model, but found 0 with names \[\]\."
    ):
        embedding_model_resolver.get_by_name(
            session=test_db, collection_id=collection_id, embedding_model_name=None
        )


def test_get_by_name__existing_name(test_db: Session) -> None:
    """Test get_by_name when embedding_model_name is provided and exists."""
    collection = create_collection(session=test_db)
    collection_id = collection.collection_id

    embedding_model_1 = create_embedding_model(
        session=test_db,
        collection_id=collection_id,
        embedding_model_name="embedding_model_1",
    )
    embedding_model_2 = create_embedding_model(
        session=test_db,
        collection_id=collection_id,
        embedding_model_name="embedding_model_2",
    )

    result = embedding_model_resolver.get_by_name(
        session=test_db, collection_id=collection_id, embedding_model_name="embedding_model_1"
    )
    assert result.embedding_model_id == embedding_model_1.embedding_model_id
    assert result.name == "embedding_model_1"

    result = embedding_model_resolver.get_by_name(
        session=test_db, collection_id=collection_id, embedding_model_name="embedding_model_2"
    )
    assert result.embedding_model_id == embedding_model_2.embedding_model_id
    assert result.name == "embedding_model_2"


def test_get_by_name__nonexistent_name(test_db: Session) -> None:
    """Test get_by_name when embedding_model_name is provided but doesn't exist."""
    collection = create_collection(session=test_db)
    collection_id = collection.collection_id

    create_embedding_model(
        session=test_db,
        collection_id=collection_id,
        embedding_model_name="embedding_model_1",
    )

    with pytest.raises(ValueError, match="Embedding model with name `nonexistent` not found."):
        embedding_model_resolver.get_by_name(
            session=test_db, collection_id=collection_id, embedding_model_name="nonexistent"
        )


def test_get_or_create__creates_new_model(test_db: Session) -> None:
    """get_or_create should insert a model when none exists for the hash."""
    collection = create_collection(session=test_db)

    model_create = EmbeddingModelCreate(
        collection_id=collection.collection_id,
        name="Model Name",
        embedding_model_hash="model_hash",
        parameter_count_in_mb=200,
        embedding_dimension=768,
    )
    created = embedding_model_resolver.get_or_create(session=test_db, embedding_model=model_create)

    assert created.embedding_model_hash == "model_hash"
    assert created.name == "Model Name"
    assert created.parameter_count_in_mb == 200
    assert created.embedding_dimension == 768
    assert created.collection_id == collection.collection_id


def test_get_or_create__reuses_existing_model(test_db: Session) -> None:
    """get_or_create should return the existing model for a matching hash."""
    collection = create_collection(session=test_db)
    existing = create_embedding_model(
        session=test_db,
        collection_id=collection.collection_id,
        embedding_model_name="Model Name",
        embedding_model_hash="model_hash",
        parameter_count_in_mb=10,
        embedding_dimension=32,
    )

    model_create = EmbeddingModelCreate(
        collection_id=collection.collection_id,
        name="Model Name",
        embedding_model_hash="model_hash",
        parameter_count_in_mb=10,
        embedding_dimension=32,
    )

    reused = embedding_model_resolver.get_or_create(session=test_db, embedding_model=model_create)

    assert reused.embedding_model_id == existing.embedding_model_id
    models = embedding_model_resolver.get_all_by_collection_id(
        session=test_db, collection_id=collection.collection_id
    )
    assert len(models) == 1


def test_get_or_create__conflicting_model_raises(test_db: Session) -> None:
    """Conflicting metadata for the same hash should raise an error."""
    collection = create_collection(session=test_db)
    create_embedding_model(
        session=test_db,
        collection_id=collection.collection_id,
        embedding_model_name="Model Name",
        embedding_model_hash="model_hash",
        parameter_count_in_mb=10,
        embedding_dimension=32,
    )

    conflicting_model_create = EmbeddingModelCreate(
        collection_id=collection.collection_id,
        name="Model Name",
        embedding_model_hash="model_hash",
        parameter_count_in_mb=2000,
        embedding_dimension=64,
    )

    with pytest.raises(
        ValueError,
        match="An embedding model with the same hash but different parameters already exists.",
    ):
        embedding_model_resolver.get_or_create(
            session=test_db, embedding_model=conflicting_model_create
        )


def test_get_or_create__same_hash_different_collections(test_db: Session) -> None:
    collection_1 = create_collection(session=test_db, collection_name="collection_1")
    collection_2 = create_collection(session=test_db, collection_name="collection_2")

    model_create_1 = EmbeddingModelCreate(
        collection_id=collection_1.collection_id,
        name="Test Model",
        embedding_model_hash="same_hash",
        parameter_count_in_mb=10,
        embedding_dimension=32,
    )
    model_1 = embedding_model_resolver.get_or_create(
        session=test_db, embedding_model=model_create_1
    )

    model_create_2 = EmbeddingModelCreate(
        collection_id=collection_2.collection_id,
        name="Test Model",
        embedding_model_hash="same_hash",
        parameter_count_in_mb=10,
        embedding_dimension=32,
    )
    model_2 = embedding_model_resolver.get_or_create(
        session=test_db, embedding_model=model_create_2
    )

    # Should be different models
    assert model_1.embedding_model_id != model_2.embedding_model_id
    assert model_1.collection_id == collection_1.collection_id
    assert model_2.collection_id == collection_2.collection_id

    # Each collection should have exactly one model
    models_1 = embedding_model_resolver.get_all_by_collection_id(
        session=test_db, collection_id=collection_1.collection_id
    )
    models_2 = embedding_model_resolver.get_all_by_collection_id(
        session=test_db, collection_id=collection_2.collection_id
    )
    assert len(models_1) == 1
    assert len(models_2) == 1
