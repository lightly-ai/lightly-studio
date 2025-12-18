from __future__ import annotations

import pytest
from sqlmodel import Session

from lightly_studio.models.embedding_model import EmbeddingModelCreate
from lightly_studio.resolvers import embedding_model_resolver
from tests.helpers_resolvers import (
    create_dataset,
    create_embedding_model,
)


def test_create_embedding_model(test_db: Session) -> None:
    dataset = create_dataset(session=test_db)
    dataset_id = dataset.collection_id
    embedding_model = create_embedding_model(
        session=test_db,
        dataset_id=dataset_id,
        embedding_model_name="example_embedding_model",
    )
    assert embedding_model.name == "example_embedding_model"


def test_read_embedding_models(test_db: Session) -> None:
    dataset = create_dataset(session=test_db)
    dataset_id = dataset.collection_id

    embedding_model_1 = create_embedding_model(
        session=test_db,
        dataset_id=dataset_id,
        embedding_model_name="embedding_model_1",
    )
    embedding_model_2 = create_embedding_model(
        session=test_db,
        dataset_id=dataset_id,
        embedding_model_name="embedding_model_2",
    )

    # Get all embedding models of a dataset.
    embedding_models = embedding_model_resolver.get_all_by_dataset_id(
        session=test_db, dataset_id=dataset_id
    )
    assert len(embedding_models) == 2

    assert embedding_models[0].embedding_model_id == embedding_model_1.embedding_model_id
    assert embedding_models[1].embedding_model_id == embedding_model_2.embedding_model_id


def test_read_embedding_model(test_db: Session) -> None:
    dataset = create_dataset(session=test_db)
    dataset_id = dataset.collection_id

    embedding_model = create_embedding_model(session=test_db, dataset_id=dataset_id)

    embedding_model_from_resolver = embedding_model_resolver.get_by_id(
        session=test_db, embedding_model_id=embedding_model.embedding_model_id
    )
    assert embedding_model_from_resolver is not None
    assert embedding_model_from_resolver.embedding_model_id == embedding_model.embedding_model_id
    assert embedding_model_from_resolver.name == embedding_model.name


def test_delete_embedding_model(test_db: Session) -> None:
    dataset = create_dataset(session=test_db)
    dataset_id = dataset.collection_id

    embedding_model = create_embedding_model(session=test_db, dataset_id=dataset_id)

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
    dataset = create_dataset(session=test_db)
    dataset_id = dataset.collection_id

    embedding_model_1 = create_embedding_model(
        session=test_db,
        dataset_id=dataset_id,
        embedding_model_name="embedding_model_1",
        embedding_model_hash="hash_1",
    )
    create_embedding_model(
        session=test_db,
        dataset_id=dataset_id,
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


def test_get_by_name__none_with_single_model(test_db: Session) -> None:
    """Test get_by_name when embedding_model_name is None and exactly one model exists."""
    dataset = create_dataset(session=test_db)
    dataset_id = dataset.collection_id

    embedding_model = create_embedding_model(
        session=test_db,
        dataset_id=dataset_id,
        embedding_model_name="embedding_model_1",
    )

    result = embedding_model_resolver.get_by_name(
        session=test_db, dataset_id=dataset_id, embedding_model_name=None
    )
    assert result.embedding_model_id == embedding_model.embedding_model_id
    assert result.name == "embedding_model_1"


def test_get_by_name__none_with_multiple_models(test_db: Session) -> None:
    """Test get_by_name when embedding_model_name is None but multiple models exist."""
    dataset = create_dataset(session=test_db)
    dataset_id = dataset.collection_id

    create_embedding_model(
        session=test_db,
        dataset_id=dataset_id,
        embedding_model_name="embedding_model_1",
    )
    create_embedding_model(
        session=test_db,
        dataset_id=dataset_id,
        embedding_model_name="embedding_model_2",
    )

    with pytest.raises(
        ValueError,
        match=r"Expected exactly one embedding model, but found 2 with names "
        r"\['embedding_model_1', 'embedding_model_2'\]\.",
    ):
        embedding_model_resolver.get_by_name(
            session=test_db, dataset_id=dataset_id, embedding_model_name=None
        )


def test_get_by_name__none_with_no_models(test_db: Session) -> None:
    """Test get_by_name when embedding_model_name is None but no models exist."""
    dataset = create_dataset(session=test_db)
    dataset_id = dataset.collection_id

    with pytest.raises(
        ValueError, match=r"Expected exactly one embedding model, but found 0 with names \[\]\."
    ):
        embedding_model_resolver.get_by_name(
            session=test_db, dataset_id=dataset_id, embedding_model_name=None
        )


def test_get_by_name__existing_name(test_db: Session) -> None:
    """Test get_by_name when embedding_model_name is provided and exists."""
    dataset = create_dataset(session=test_db)
    dataset_id = dataset.collection_id

    embedding_model_1 = create_embedding_model(
        session=test_db,
        dataset_id=dataset_id,
        embedding_model_name="embedding_model_1",
    )
    embedding_model_2 = create_embedding_model(
        session=test_db,
        dataset_id=dataset_id,
        embedding_model_name="embedding_model_2",
    )

    result = embedding_model_resolver.get_by_name(
        session=test_db, dataset_id=dataset_id, embedding_model_name="embedding_model_1"
    )
    assert result.embedding_model_id == embedding_model_1.embedding_model_id
    assert result.name == "embedding_model_1"

    result = embedding_model_resolver.get_by_name(
        session=test_db, dataset_id=dataset_id, embedding_model_name="embedding_model_2"
    )
    assert result.embedding_model_id == embedding_model_2.embedding_model_id
    assert result.name == "embedding_model_2"


def test_get_by_name__nonexistent_name(test_db: Session) -> None:
    """Test get_by_name when embedding_model_name is provided but doesn't exist."""
    dataset = create_dataset(session=test_db)
    dataset_id = dataset.collection_id

    create_embedding_model(
        session=test_db,
        dataset_id=dataset_id,
        embedding_model_name="embedding_model_1",
    )

    with pytest.raises(ValueError, match="Embedding model with name `nonexistent` not found."):
        embedding_model_resolver.get_by_name(
            session=test_db, dataset_id=dataset_id, embedding_model_name="nonexistent"
        )


def test_get_or_create__creates_new_model(test_db: Session) -> None:
    """get_or_create should insert a model when none exists for the hash."""
    dataset = create_dataset(session=test_db)

    model_create = EmbeddingModelCreate(
        collection_id=dataset.collection_id,
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
    assert created.collection_id == dataset.collection_id


def test_get_or_create__reuses_existing_model(test_db: Session) -> None:
    """get_or_create should return the existing model for a matching hash."""
    dataset = create_dataset(session=test_db)
    existing = create_embedding_model(
        session=test_db,
        dataset_id=dataset.collection_id,
        embedding_model_name="Model Name",
        embedding_model_hash="model_hash",
        parameter_count_in_mb=10,
        embedding_dimension=32,
    )

    model_create = EmbeddingModelCreate(
        collection_id=dataset.collection_id,
        name="Model Name",
        embedding_model_hash="model_hash",
        parameter_count_in_mb=10,
        embedding_dimension=32,
    )

    reused = embedding_model_resolver.get_or_create(session=test_db, embedding_model=model_create)

    assert reused.embedding_model_id == existing.embedding_model_id
    models = embedding_model_resolver.get_all_by_dataset_id(
        session=test_db, dataset_id=dataset.collection_id
    )
    assert len(models) == 1


def test_get_or_create__conflicting_model_raises(test_db: Session) -> None:
    """Conflicting metadata for the same hash should raise an error."""
    dataset = create_dataset(session=test_db)
    create_embedding_model(
        session=test_db,
        dataset_id=dataset.collection_id,
        embedding_model_name="Model Name",
        embedding_model_hash="model_hash",
        parameter_count_in_mb=10,
        embedding_dimension=32,
    )

    conflicting_model_create = EmbeddingModelCreate(
        collection_id=dataset.collection_id,
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
