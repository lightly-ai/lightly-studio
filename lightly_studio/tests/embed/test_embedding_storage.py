"""Tests for embedding validation and persistence."""

from __future__ import annotations

from uuid import UUID, uuid4

import numpy as np
import pytest
from pytest_mock import MockerFixture
from sqlmodel import Session, select

from lightly_studio.embed import embedding_storage
from lightly_studio.models.collection import CollectionTable
from lightly_studio.models.sample_embedding import SampleEmbeddingTable
from lightly_studio.resolvers import sample_embedding_resolver
from tests.helpers_resolvers import (
    ImageStub,
    create_embedding_model,
    create_image,
    create_images,
)

_EMBEDDING_DIMENSION = 3


def test_validate_and_coerce_embeddings(
    db_session: Session,
    collection: CollectionTable,
) -> None:
    """A well-formed batch of embeddings passes validation unchanged."""
    model_id = _create_model(session=db_session, collection=collection)
    sample_ids = [uuid4(), uuid4()]
    embeddings = np.zeros((2, _EMBEDDING_DIMENSION), dtype=np.float32)

    result = embedding_storage._validate_and_coerce_embeddings(
        session=db_session, model_id=model_id, sample_ids=sample_ids, embeddings=embeddings
    )

    assert result.dtype == np.float32
    np.testing.assert_array_equal(result, embeddings)


def test_validate_and_coerce_embeddings__empty_is_valid(
    db_session: Session,
    collection: CollectionTable,
) -> None:
    """An empty batch passes validation without touching the embedding model."""
    model_id = _create_model(session=db_session, collection=collection)

    result = embedding_storage._validate_and_coerce_embeddings(
        session=db_session,
        model_id=model_id,
        sample_ids=[],
        embeddings=np.zeros((0, _EMBEDDING_DIMENSION), dtype=np.float32),
    )

    assert len(result) == 0


def test_validate_and_coerce_embeddings__rejects_non_2d_array(
    db_session: Session,
    collection: CollectionTable,
) -> None:
    """A 0-D array raises a clear ValueError instead of TypeError from `len()`."""
    model_id = _create_model(session=db_session, collection=collection)
    sample_ids = [uuid4()]
    embeddings = np.array(1.0, dtype=np.float32)

    with pytest.raises(ValueError, match=r"must be a 2-D array .* got a 0-D array"):
        embedding_storage._validate_and_coerce_embeddings(
            session=db_session,
            model_id=model_id,
            sample_ids=sample_ids,
            embeddings=embeddings,
        )


def test_validate_and_coerce_embeddings__count_mismatch(
    db_session: Session,
    collection: CollectionTable,
) -> None:
    """A different number of embeddings and sample IDs raises a clear error."""
    model_id = _create_model(session=db_session, collection=collection)
    sample_ids = [uuid4(), uuid4()]
    embeddings = np.zeros((1, _EMBEDDING_DIMENSION), dtype=np.float32)

    with pytest.raises(ValueError, match=r"does not match number of sample IDs"):
        embedding_storage._validate_and_coerce_embeddings(
            session=db_session, model_id=model_id, sample_ids=sample_ids, embeddings=embeddings
        )


def test_validate_and_coerce_embeddings__wrong_dimension(
    db_session: Session,
    collection: CollectionTable,
) -> None:
    """A vector whose length does not match the model dimension raises a clear error."""
    model_id = _create_model(session=db_session, collection=collection)
    sample_ids = [uuid4()]
    wrong_dimension = _EMBEDDING_DIMENSION + 1
    embeddings = np.zeros((1, wrong_dimension), dtype=np.float32)

    with pytest.raises(ValueError, match=rf"Embedding dimension \({wrong_dimension}\)"):
        embedding_storage._validate_and_coerce_embeddings(
            session=db_session, model_id=model_id, sample_ids=sample_ids, embeddings=embeddings
        )


def test_validate_and_coerce_embeddings__casts_float64_to_float32(
    db_session: Session,
    collection: CollectionTable,
) -> None:
    """A float64 array is safely cast down to float32."""
    model_id = _create_model(session=db_session, collection=collection)
    sample_ids = [uuid4()]
    embeddings = np.array([[0.1 * (i + 1) for i in range(_EMBEDDING_DIMENSION)]], dtype=np.float64)

    result = embedding_storage._validate_and_coerce_embeddings(
        session=db_session,
        model_id=model_id,
        sample_ids=sample_ids,
        embeddings=embeddings,  # type: ignore[arg-type]
    )

    assert result.dtype == np.float32
    np.testing.assert_allclose(result, embeddings, rtol=1e-6)


def test_validate_and_coerce_embeddings__rejects_non_numeric_dtype(
    db_session: Session,
    collection: CollectionTable,
) -> None:
    """A non-numeric dtype is rejected."""
    model_id = _create_model(session=db_session, collection=collection)
    sample_ids = [uuid4()]
    embeddings = np.array([[f"s{i}" for i in range(_EMBEDDING_DIMENSION)]])

    with pytest.raises(ValueError, match=r"must be numeric"):
        embedding_storage._validate_and_coerce_embeddings(
            session=db_session,
            model_id=model_id,
            sample_ids=sample_ids,
            embeddings=embeddings,
        )


@pytest.mark.parametrize("invalid_value", [np.nan, np.inf, 1e308])
def test_validate_and_coerce_embeddings__rejects_non_finite_values(
    db_session: Session,
    collection: CollectionTable,
    invalid_value: float,
) -> None:
    """Non-finite values before or after float32 coercion are rejected."""
    model_id = _create_model(session=db_session, collection=collection)
    sample_ids = [uuid4()]
    embeddings = np.zeros((1, _EMBEDDING_DIMENSION), dtype=np.float64)
    embeddings[0, 0] = invalid_value

    with pytest.raises(ValueError, match=r"NaN or infinite"):
        embedding_storage._validate_and_coerce_embeddings(
            session=db_session,
            model_id=model_id,
            sample_ids=sample_ids,
            embeddings=embeddings,  # type: ignore[arg-type]
        )


def test_store_embeddings__rejects_invalid_embeddings_before_write(
    db_session: Session,
    collection: CollectionTable,
) -> None:
    """Invalid embeddings raise before anything is written to the database."""
    model_id = _create_model(session=db_session, collection=collection)
    sample_ids = [uuid4()]
    embeddings = np.full((1, _EMBEDDING_DIMENSION), np.nan, dtype=np.float32)

    with pytest.raises(ValueError, match=r"NaN or infinite"):
        embedding_storage.store_embeddings(
            session=db_session,
            model_id=model_id,
            sample_ids=sample_ids,
            embeddings=embeddings,
            show_progress=False,
        )

    stored_embeddings = db_session.exec(
        select(SampleEmbeddingTable).where(SampleEmbeddingTable.embedding_model_id == model_id)
    ).all()
    assert len(stored_embeddings) == 0


def test_store_embeddings__casts_and_batches_embeddings(
    db_session: Session,
    collection: CollectionTable,
    mocker: MockerFixture,
) -> None:
    """Storage casts float64 values and inserts them in bounded batches."""
    mocker.patch.object(embedding_storage, "EMBEDDING_INSERTION_BATCH_SIZE", 4)
    create_many_spy = mocker.spy(sample_embedding_resolver, "create_many")
    model_id = _create_model(session=db_session, collection=collection)
    # 10 samples with batch size 4 -> 3 batches of sizes 4, 4, and 2.
    images = create_images(
        db_session=db_session,
        collection_id=collection.collection_id,
        images=[ImageStub() for _ in range(10)],
    )
    sample_ids = [image.sample_id for image in images]
    embeddings = np.zeros((len(sample_ids), _EMBEDDING_DIMENSION), dtype=np.float64)

    embedding_storage.store_embeddings(
        session=db_session,
        model_id=model_id,
        sample_ids=sample_ids,
        embeddings=embeddings,  # type: ignore[arg-type]
        show_progress=False,
    )

    assert create_many_spy.call_count == 3
    stored_embeddings = db_session.exec(
        select(SampleEmbeddingTable).where(SampleEmbeddingTable.embedding_model_id == model_id)
    ).all()
    assert len(stored_embeddings) == len(sample_ids)
    assert all(embedding.embedding.dtype == np.float32 for embedding in stored_embeddings)


def test_store_embeddings__casts_float64_embeddings(
    db_session: Session,
    collection: CollectionTable,
) -> None:
    """Storage accepts and stores embeddings passed in as float64."""
    model_id = _create_model(session=db_session, collection=collection)
    image = create_image(session=db_session, collection_id=collection.collection_id)
    sample_ids = [image.sample_id]
    embeddings = np.array([[0.1 * (i + 1) for i in range(_EMBEDDING_DIMENSION)]], dtype=np.float64)

    embedding_storage.store_embeddings(
        session=db_session,
        model_id=model_id,
        sample_ids=sample_ids,
        embeddings=embeddings,  # type: ignore[arg-type]
        show_progress=False,
    )

    stored_embeddings = db_session.exec(
        select(SampleEmbeddingTable).where(SampleEmbeddingTable.embedding_model_id == model_id)
    ).all()
    assert len(stored_embeddings) == 1
    assert len(stored_embeddings[0].embedding) == _EMBEDDING_DIMENSION


def _create_model(session: Session, collection: CollectionTable) -> UUID:
    model = create_embedding_model(
        session=session,
        collection_id=collection.collection_id,
        embedding_dimension=_EMBEDDING_DIMENSION,
    )
    return model.embedding_model_id
