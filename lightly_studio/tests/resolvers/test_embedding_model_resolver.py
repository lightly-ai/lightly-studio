from __future__ import annotations

from uuid import UUID

import pytest
from sqlmodel import Session

from lightly_studio.models.embedding_model import EmbeddingModelCreate
from lightly_studio.resolvers import (
    default_embedding_space_resolver,
    embedding_model_resolver,
)
from tests.helpers_resolvers import (
    create_collection,
    create_embedding_model,
    create_image,
    create_sample_embedding,
)


def _attach_model_to_collection(
    session: Session,
    collection_id: UUID,
    embedding_model_id: UUID,
    file_path_abs: str,
) -> None:
    """Give an embedding model an embedding in a collection.

    Embedding models are a shared global registry; they belong to a collection only
    through the samples they embedded. This creates one image sample and one embedding so
    ``get_all_by_collection_id`` and ``get_by_name`` see the model in the collection.
    """
    image = create_image(session=session, collection_id=collection_id, file_path_abs=file_path_abs)
    create_sample_embedding(
        session=session,
        sample_id=image.sample_id,
        embedding_model_id=embedding_model_id,
        embedding=[0.0, 0.0],
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


def test_read_embedding_models(db_session: Session) -> None:
    collection = create_collection(session=db_session)
    collection_id = collection.collection_id

    embedding_model_1 = create_embedding_model(
        session=db_session,
        collection_id=collection_id,
        embedding_model_name="embedding_model_1",
        embedding_model_hash="hash_1",
    )
    embedding_model_2 = create_embedding_model(
        session=db_session,
        collection_id=collection_id,
        embedding_model_name="embedding_model_2",
        embedding_model_hash="hash_2",
    )
    _attach_model_to_collection(
        session=db_session,
        collection_id=collection_id,
        embedding_model_id=embedding_model_1.embedding_model_id,
        file_path_abs="sample_1.jpg",
    )
    _attach_model_to_collection(
        session=db_session,
        collection_id=collection_id,
        embedding_model_id=embedding_model_2.embedding_model_id,
        file_path_abs="sample_2.jpg",
    )

    # Get all embedding models with an embedding in the collection, oldest first.
    embedding_models = embedding_model_resolver.get_all_by_collection_id(
        session=db_session, collection_id=collection_id
    )
    assert len(embedding_models) == 2
    assert embedding_models[0].embedding_model_id == embedding_model_1.embedding_model_id
    assert embedding_models[1].embedding_model_id == embedding_model_2.embedding_model_id


def test_read_embedding_models__scoped_to_collection(db_session: Session) -> None:
    """A model is listed for a collection only if it has an embedding there."""
    collection_1 = create_collection(session=db_session, collection_name="collection_1")
    collection_2 = create_collection(session=db_session, collection_name="collection_2")

    model = create_embedding_model(
        session=db_session,
        collection_id=collection_1.collection_id,
        embedding_model_name="shared_model",
    )
    _attach_model_to_collection(
        session=db_session,
        collection_id=collection_1.collection_id,
        embedding_model_id=model.embedding_model_id,
        file_path_abs="sample_1.jpg",
    )

    models_1 = embedding_model_resolver.get_all_by_collection_id(
        session=db_session, collection_id=collection_1.collection_id
    )
    models_2 = embedding_model_resolver.get_all_by_collection_id(
        session=db_session, collection_id=collection_2.collection_id
    )
    assert [m.embedding_model_id for m in models_1] == [model.embedding_model_id]
    assert models_2 == []


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


def test_delete_embedding_model(db_session: Session) -> None:
    collection = create_collection(session=db_session)
    collection_id = collection.collection_id

    embedding_model = create_embedding_model(session=db_session, collection_id=collection_id)

    # The first model becomes the collection default; its default_embedding_space row must
    # be removed before the model can be deleted (foreign key).
    default_embedding_space_resolver.delete_by_collection_id(
        session=db_session, collection_id=collection_id
    )

    embedding_model_resolver.delete(
        session=db_session, embedding_model_id=embedding_model.embedding_model_id
    )

    embedding_model_deleted = embedding_model_resolver.get_by_id(
        session=db_session, embedding_model_id=embedding_model.embedding_model_id
    )
    assert embedding_model_deleted is None


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
        session=db_session, embedding_model_hash="hash_1"
    )
    assert embedding_model is not None
    assert embedding_model.name == embedding_model_1.name

    embedding_model = embedding_model_resolver.get_by_model_hash(
        session=db_session, embedding_model_hash="hash_3"
    )
    assert embedding_model is None


def test_get_by_model_hash__dedup_across_collections(db_session: Session) -> None:
    """Models are deduplicated globally by hash: same weights map to one shared row."""
    collection_1 = create_collection(session=db_session, collection_name="collection_1")
    collection_2 = create_collection(session=db_session, collection_name="collection_2")

    model = create_embedding_model(
        session=db_session,
        collection_id=collection_1.collection_id,
        embedding_model_name="shared_model",
        embedding_model_hash="same_hash",
    )

    # A second collection re-using the same hash resolves the same shared row.
    reused = embedding_model_resolver.get_or_create(
        session=db_session,
        embedding_model=EmbeddingModelCreate(
            name="shared_model",
            embedding_model_hash="same_hash",
            parameter_count_in_mb=model.parameter_count_in_mb,
            embedding_dimension=model.embedding_dimension,
        ),
    )
    assert reused.embedding_model_id == model.embedding_model_id

    result = embedding_model_resolver.get_by_model_hash(
        session=db_session, embedding_model_hash="same_hash"
    )
    assert result is not None
    assert result.embedding_model_id == model.embedding_model_id

    # The collections share a single embedding model row.
    default_1 = default_embedding_space_resolver.set_default(
        session=db_session,
        collection_id=collection_2.collection_id,
        embedding_model_id=reused.embedding_model_id,
    )
    assert default_1.embedding_model_id == model.embedding_model_id


def test_get_by_name__none_with_single_model(db_session: Session) -> None:
    """Test get_by_name when embedding_model_name is None and exactly one model exists."""
    collection = create_collection(session=db_session)
    collection_id = collection.collection_id

    embedding_model = create_embedding_model(
        session=db_session,
        collection_id=collection_id,
        embedding_model_name="embedding_model_1",
    )
    _attach_model_to_collection(
        session=db_session,
        collection_id=collection_id,
        embedding_model_id=embedding_model.embedding_model_id,
        file_path_abs="sample_1.jpg",
    )

    result = embedding_model_resolver.get_by_name(
        session=db_session, collection_id=collection_id, embedding_model_name=None
    )
    assert result.embedding_model_id == embedding_model.embedding_model_id
    assert result.name == "embedding_model_1"


def test_get_by_name__none_with_multiple_models(db_session: Session) -> None:
    """Test get_by_name when embedding_model_name is None but multiple models exist."""
    collection = create_collection(session=db_session)
    collection_id = collection.collection_id

    model_1 = create_embedding_model(
        session=db_session,
        collection_id=collection_id,
        embedding_model_name="embedding_model_1",
        embedding_model_hash="hash_1",
    )
    model_2 = create_embedding_model(
        session=db_session,
        collection_id=collection_id,
        embedding_model_name="embedding_model_2",
        embedding_model_hash="hash_2",
    )
    _attach_model_to_collection(
        session=db_session,
        collection_id=collection_id,
        embedding_model_id=model_1.embedding_model_id,
        file_path_abs="sample_1.jpg",
    )
    _attach_model_to_collection(
        session=db_session,
        collection_id=collection_id,
        embedding_model_id=model_2.embedding_model_id,
        file_path_abs="sample_2.jpg",
    )

    with pytest.raises(
        ValueError,
        match=r"Expected exactly one embedding model, but found 2 with names "
        r"\['embedding_model_1', 'embedding_model_2'\]\.",
    ):
        embedding_model_resolver.get_by_name(
            session=db_session, collection_id=collection_id, embedding_model_name=None
        )


def test_get_by_name__none_with_no_models(db_session: Session) -> None:
    """Test get_by_name when embedding_model_name is None but no models exist."""
    collection = create_collection(session=db_session)
    collection_id = collection.collection_id

    with pytest.raises(
        ValueError, match=r"Expected exactly one embedding model, but found 0 with names \[\]\."
    ):
        embedding_model_resolver.get_by_name(
            session=db_session, collection_id=collection_id, embedding_model_name=None
        )


def test_get_by_name__existing_name(db_session: Session) -> None:
    """Test get_by_name when embedding_model_name is provided and exists."""
    collection = create_collection(session=db_session)
    collection_id = collection.collection_id

    embedding_model_1 = create_embedding_model(
        session=db_session,
        collection_id=collection_id,
        embedding_model_name="embedding_model_1",
        embedding_model_hash="hash_1",
    )
    embedding_model_2 = create_embedding_model(
        session=db_session,
        collection_id=collection_id,
        embedding_model_name="embedding_model_2",
        embedding_model_hash="hash_2",
    )
    _attach_model_to_collection(
        session=db_session,
        collection_id=collection_id,
        embedding_model_id=embedding_model_1.embedding_model_id,
        file_path_abs="sample_1.jpg",
    )
    _attach_model_to_collection(
        session=db_session,
        collection_id=collection_id,
        embedding_model_id=embedding_model_2.embedding_model_id,
        file_path_abs="sample_2.jpg",
    )

    result = embedding_model_resolver.get_by_name(
        session=db_session, collection_id=collection_id, embedding_model_name="embedding_model_1"
    )
    assert result.embedding_model_id == embedding_model_1.embedding_model_id
    assert result.name == "embedding_model_1"

    result = embedding_model_resolver.get_by_name(
        session=db_session, collection_id=collection_id, embedding_model_name="embedding_model_2"
    )
    assert result.embedding_model_id == embedding_model_2.embedding_model_id
    assert result.name == "embedding_model_2"


def test_get_by_name__nonexistent_name(db_session: Session) -> None:
    """Test get_by_name when embedding_model_name is provided but doesn't exist."""
    collection = create_collection(session=db_session)
    collection_id = collection.collection_id

    model = create_embedding_model(
        session=db_session,
        collection_id=collection_id,
        embedding_model_name="embedding_model_1",
    )
    _attach_model_to_collection(
        session=db_session,
        collection_id=collection_id,
        embedding_model_id=model.embedding_model_id,
        file_path_abs="sample_1.jpg",
    )

    with pytest.raises(ValueError, match=r"Embedding model with name `nonexistent` not found."):
        embedding_model_resolver.get_by_name(
            session=db_session, collection_id=collection_id, embedding_model_name="nonexistent"
        )


def test_get_or_create__creates_new_model(db_session: Session) -> None:
    """get_or_create should insert a model when none exists for the hash."""
    model_create = EmbeddingModelCreate(
        name="Model Name",
        embedding_model_hash="model_hash",
        parameter_count_in_mb=200,
        embedding_dimension=768,
    )
    created = embedding_model_resolver.get_or_create(
        session=db_session, embedding_model=model_create
    )

    assert created.embedding_model_hash == "model_hash"
    assert created.name == "Model Name"
    assert created.parameter_count_in_mb == 200
    assert created.embedding_dimension == 768


def test_get_or_create__reuses_existing_model(db_session: Session) -> None:
    """get_or_create should return the existing model for a matching hash."""
    collection = create_collection(session=db_session)
    existing = create_embedding_model(
        session=db_session,
        collection_id=collection.collection_id,
        embedding_model_name="Model Name",
        embedding_model_hash="model_hash",
        parameter_count_in_mb=10,
        embedding_dimension=32,
    )

    model_create = EmbeddingModelCreate(
        name="Model Name",
        embedding_model_hash="model_hash",
        parameter_count_in_mb=10,
        embedding_dimension=32,
    )

    reused = embedding_model_resolver.get_or_create(
        session=db_session, embedding_model=model_create
    )

    assert reused.embedding_model_id == existing.embedding_model_id


def test_get_or_create__conflicting_model_raises(db_session: Session) -> None:
    """Conflicting metadata for the same hash should raise an error."""
    collection = create_collection(session=db_session)
    create_embedding_model(
        session=db_session,
        collection_id=collection.collection_id,
        embedding_model_name="Model Name",
        embedding_model_hash="model_hash",
        parameter_count_in_mb=10,
        embedding_dimension=32,
    )

    conflicting_model_create = EmbeddingModelCreate(
        name="Model Name",
        embedding_model_hash="model_hash",
        parameter_count_in_mb=2000,
        embedding_dimension=64,
    )

    with pytest.raises(
        ValueError,
        match=r"An embedding model with the same hash but different parameters already exists.",
    ):
        embedding_model_resolver.get_or_create(
            session=db_session, embedding_model=conflicting_model_create
        )


def test_get_or_create__same_hash_shared_across_collections(db_session: Session) -> None:
    """Same hash used from two collections resolves to a single shared model row."""
    model_create_1 = EmbeddingModelCreate(
        name="Test Model",
        embedding_model_hash="same_hash",
        parameter_count_in_mb=10,
        embedding_dimension=32,
    )
    model_1 = embedding_model_resolver.get_or_create(
        session=db_session, embedding_model=model_create_1
    )

    model_create_2 = EmbeddingModelCreate(
        name="Test Model",
        embedding_model_hash="same_hash",
        parameter_count_in_mb=10,
        embedding_dimension=32,
    )
    model_2 = embedding_model_resolver.get_or_create(
        session=db_session, embedding_model=model_create_2
    )

    # The same weights map to one shared row.
    assert model_1.embedding_model_id == model_2.embedding_model_id
