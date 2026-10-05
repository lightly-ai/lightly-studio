from __future__ import annotations

from uuid import UUID

import numpy as np
import pytest
from pytest_mock import MockerFixture
from sqlmodel import Session, col, delete

from lightly_studio.models.sample_embedding import SampleEmbeddingTable
from lightly_studio.resolvers import twodim_embedding_resolver
from tests import helpers_resolvers
from tests.helpers_resolvers import (
    ImageStub,
)


def test__calculate_2d_embeddings__1_sample() -> None:
    embedding_values = [np.array([0.1, 0.2, 0.3], dtype=np.float32)]
    projected = twodim_embedding_resolver._calculate_2d_embeddings(embedding_values)
    assert projected == [(0.0, 0.0)]


def test__calculate_2d_embeddings__2_samples() -> None:
    embedding_values = [
        np.array([0.1, 0.2, 0.3], dtype=np.float32),
        np.array([0.4, 0.5, 0.6], dtype=np.float32),
    ]
    projected = twodim_embedding_resolver._calculate_2d_embeddings(embedding_values)
    assert projected == [(0.0, 0.0), (1.0, 1.0)]


def test_get_twodim_embeddings__no_samples(
    db_session: Session,
) -> None:
    collection = helpers_resolvers.create_collection(
        session=db_session, collection_name="no_samples"
    )
    embedding_model = helpers_resolvers.create_embedding_model(
        session=db_session,
        collection_id=collection.collection_id,
        embedding_dimension=3,
    )

    x_values, y_values, sample_ids = twodim_embedding_resolver.get_twodim_embeddings(
        session=db_session,
        collection_id=collection.collection_id,
        embedding_model_id=embedding_model.embedding_model_id,
    )

    assert len(x_values) == 0
    assert len(y_values) == 0
    assert sample_ids == []


def test_get_twodim_embeddings__no_samples_with_embeddings(
    db_session: Session,
) -> None:
    collection = helpers_resolvers.create_collection(
        session=db_session, collection_name="missing_embeddings"
    )
    embedding_model = helpers_resolvers.create_embedding_model(
        session=db_session,
        collection_id=collection.collection_id,
        embedding_dimension=3,
    )
    helpers_resolvers.create_image(
        session=db_session,
        collection_id=collection.collection_id,
        file_path_abs="sample_missing_embedding.jpg",
    )

    x_values, y_values, sample_ids = twodim_embedding_resolver.get_twodim_embeddings(
        session=db_session,
        collection_id=collection.collection_id,
        embedding_model_id=embedding_model.embedding_model_id,
    )

    assert len(x_values) == 0
    assert len(y_values) == 0
    assert sample_ids == []


def test_get_twodim_embeddings__cache_hit(
    db_session: Session,
    mocker: MockerFixture,
) -> None:
    # Create collection, embedding model, samples, and embeddings.
    collection = helpers_resolvers.create_collection(
        session=db_session, collection_name="cache_hit_collection"
    )
    embedding_model = helpers_resolvers.create_embedding_model(
        session=db_session,
        collection_id=collection.collection_id,
        embedding_dimension=3,
    )

    helpers_resolvers.create_samples_with_embeddings(
        session=db_session,
        collection_id=collection.collection_id,
        embedding_model_id=embedding_model.embedding_model_id,
        images_and_embeddings=[
            (ImageStub(path="sample_1.jpg"), [0.1, 0.2, 0.3]),
            (ImageStub(path="sample_2.jpg"), [0.4, 0.5, 0.6]),
        ],
    )
    calculate_spy = mocker.spy(twodim_embedding_resolver, "_calculate_2d_embeddings")

    # First call - should call _calculate_2d_embeddings.
    x_first, y_first, sample_ids_first_call = twodim_embedding_resolver.get_twodim_embeddings(
        session=db_session,
        collection_id=collection.collection_id,
        embedding_model_id=embedding_model.embedding_model_id,
    )
    calculate_spy.assert_called_once()

    assert x_first.shape == (2,)
    assert y_first.shape == (2,)
    assert len(sample_ids_first_call) == 2

    # Second call - should use cache, not call _calculate_2d_embeddings again.
    x_second, y_second, sample_ids_second_call = twodim_embedding_resolver.get_twodim_embeddings(
        session=db_session,
        collection_id=collection.collection_id,
        embedding_model_id=embedding_model.embedding_model_id,
    )

    calculate_spy.assert_called_once()
    np.testing.assert_allclose(x_first, x_second)
    np.testing.assert_allclose(y_first, y_second)
    assert sample_ids_first_call == sample_ids_second_call

    # Third call after adding a sample without embeddings - should still use cache.
    helpers_resolvers.create_image(
        session=db_session,
        collection_id=collection.collection_id,
        file_path_abs="sample_3.jpg",
    )
    x_third, y_third, sample_ids_third_call = twodim_embedding_resolver.get_twodim_embeddings(
        session=db_session,
        collection_id=collection.collection_id,
        embedding_model_id=embedding_model.embedding_model_id,
    )
    calculate_spy.assert_called_once()
    np.testing.assert_allclose(x_first, x_third)
    np.testing.assert_allclose(y_first, y_third)
    assert sample_ids_first_call == sample_ids_third_call


def test_get_twodim_embeddings__recomputes_when_samples_change(
    db_session: Session,
    mocker: MockerFixture,
) -> None:
    # Create collection, embedding model, samples, and embeddings.
    collection = helpers_resolvers.create_collection(
        session=db_session, collection_name="cache_miss_collection"
    )
    embedding_model = helpers_resolvers.create_embedding_model(
        session=db_session,
        collection_id=collection.collection_id,
        embedding_dimension=3,
    )

    first_sample = helpers_resolvers.create_image(
        session=db_session,
        collection_id=collection.collection_id,
        file_path_abs="/sample_0.jpg",
    )
    helpers_resolvers.create_sample_embedding(
        session=db_session,
        sample_id=first_sample.sample_id,
        embedding_model_id=embedding_model.embedding_model_id,
        embedding=[0.1, 0.1, 0.1],
    )

    calculate_spy = mocker.spy(twodim_embedding_resolver, "_calculate_2d_embeddings")

    # First call - should call _calculate_2d_embeddings.
    x_first, y_first, sample_ids_first = twodim_embedding_resolver.get_twodim_embeddings(
        session=db_session,
        collection_id=collection.collection_id,
        embedding_model_id=embedding_model.embedding_model_id,
    )

    assert calculate_spy.call_count == 1
    assert x_first.shape == (1,)
    assert y_first.shape == (1,)
    assert len(sample_ids_first) == 1

    # Add another sample and embedding.
    second_sample = helpers_resolvers.create_image(
        session=db_session,
        collection_id=collection.collection_id,
        file_path_abs="/sample_1.jpg",
    )
    helpers_resolvers.create_sample_embedding(
        session=db_session,
        sample_id=second_sample.sample_id,
        embedding_model_id=embedding_model.embedding_model_id,
        embedding=[0.2, 0.2, 0.2],
    )

    # Second call - should recompute since samples changed.
    x_second, y_second, sample_ids_second = twodim_embedding_resolver.get_twodim_embeddings(
        session=db_session,
        collection_id=collection.collection_id,
        embedding_model_id=embedding_model.embedding_model_id,
    )

    assert calculate_spy.call_count == 2
    assert x_second.shape == (2,)
    assert y_second.shape == (2,)
    assert len(sample_ids_second) == 2


def test_get_twodim_embeddings_from_axes(db_session: Session) -> None:
    collection_id, embedding_model_id, (sample_a, sample_b) = _create_samples(
        session=db_session, embeddings=[[1.0, 2.0, 3.0], [4.0, 5.0, 6.0]]
    )

    x_values, y_values, sample_ids = twodim_embedding_resolver.get_twodim_embeddings_from_axes(
        session=db_session,
        collection_id=collection_id,
        embedding_model_id=embedding_model_id,
        direction_x=[1.0, 0.0, 10.0],
        direction_y=[0.0, 0.5, 0.0],
    )

    # The values are dot products and are not rescaled, for example 1 * 1 + 10 * 3 = 31.
    assert dict(zip(sample_ids, x_values.tolist())) == pytest.approx(
        {sample_a: 31.0, sample_b: 64.0}
    )
    assert dict(zip(sample_ids, y_values.tolist())) == pytest.approx({sample_a: 1.0, sample_b: 2.5})


def test_get_twodim_embeddings_from_axes__no_embeddings(db_session: Session) -> None:
    collection_id, embedding_model_id, _ = _create_samples(session=db_session, embeddings=[])

    x_values, y_values, sample_ids = twodim_embedding_resolver.get_twodim_embeddings_from_axes(
        session=db_session,
        collection_id=collection_id,
        embedding_model_id=embedding_model_id,
        direction_x=[1.0, 0.0, 0.0],
        direction_y=[0.0, 1.0, 0.0],
    )

    assert len(x_values) == 0
    assert len(y_values) == 0
    assert sample_ids == []


def test_get_twodim_embeddings_from_axes__dimension_mismatch(db_session: Session) -> None:
    collection = helpers_resolvers.create_collection(session=db_session)
    embedding_model = helpers_resolvers.create_embedding_model(
        session=db_session,
        collection_id=collection.collection_id,
        embedding_dimension=3,
    )

    with pytest.raises(ValueError, match="embedding dimension 3, got 2 and 3"):
        twodim_embedding_resolver.get_twodim_embeddings_from_axes(
            session=db_session,
            collection_id=collection.collection_id,
            embedding_model_id=embedding_model.embedding_model_id,
            direction_x=[1.0, 0.0],
            direction_y=[0.0, 1.0, 0.0],
        )


def test_get_twodim_embeddings_from_axes__reflects_replaced_embeddings(
    db_session: Session,
) -> None:
    collection_id, embedding_model_id, (old_sample_id,) = _create_samples(
        session=db_session, embeddings=[[0.0, 2.0, 0.0]]
    )
    twodim_embedding_resolver.get_twodim_embeddings_from_axes(
        session=db_session,
        collection_id=collection_id,
        embedding_model_id=embedding_model_id,
        direction_x=[1.0, 0.0, 0.0],
        direction_y=[0.0, 1.0, 0.0],
    )
    db_session.exec(
        delete(SampleEmbeddingTable).where(col(SampleEmbeddingTable.sample_id) == old_sample_id)
    )
    (new_image,) = helpers_resolvers.create_samples_with_embeddings(
        session=db_session,
        collection_id=collection_id,
        embedding_model_id=embedding_model_id,
        images_and_embeddings=[(ImageStub(path="sample_new.jpg"), [0.0, 9.0, 0.0])],
    )

    x_values, y_values, sample_ids = twodim_embedding_resolver.get_twodim_embeddings_from_axes(
        session=db_session,
        collection_id=collection_id,
        embedding_model_id=embedding_model_id,
        direction_x=[1.0, 0.0, 0.0],
        direction_y=[0.0, 1.0, 0.0],
    )

    assert sample_ids == [new_image.sample_id]
    assert x_values.tolist() == pytest.approx([0.0])
    assert y_values.tolist() == pytest.approx([9.0])


def test_get_twodim_embeddings_from_axes__only_includes_the_collection_and_model(
    db_session: Session,
) -> None:
    collection_id, embedding_model_id, (sample_id,) = _create_samples(
        session=db_session, embeddings=[[1.0, 2.0, 3.0]]
    )
    other_embedding_model = helpers_resolvers.create_embedding_model(
        session=db_session,
        collection_id=collection_id,
        embedding_model_name="other_model",
        embedding_dimension=3,
    )
    helpers_resolvers.create_sample_embedding(
        session=db_session,
        sample_id=sample_id,
        embedding_model_id=other_embedding_model.embedding_model_id,
        embedding=[4.0, 5.0, 6.0],
    )
    other_collection = helpers_resolvers.create_collection(session=db_session)
    helpers_resolvers.create_samples_with_embeddings(
        session=db_session,
        collection_id=other_collection.collection_id,
        embedding_model_id=embedding_model_id,
        images_and_embeddings=[(ImageStub(path="sample_other.jpg"), [7.0, 8.0, 9.0])],
    )

    x_values, y_values, sample_ids = twodim_embedding_resolver.get_twodim_embeddings_from_axes(
        session=db_session,
        collection_id=collection_id,
        embedding_model_id=embedding_model_id,
        direction_x=[1.0, 0.0, 0.0],
        direction_y=[0.0, 1.0, 0.0],
    )

    assert sample_ids == [sample_id]
    assert x_values.tolist() == pytest.approx([1.0])
    assert y_values.tolist() == pytest.approx([2.0])


def _create_samples(
    session: Session, embeddings: list[list[float]]
) -> tuple[UUID, UUID, list[UUID]]:
    """Create a collection with a 3D embedding model and one sample for each embedding.

    Returns:
        Tuple of (collection ID, embedding model ID, sample IDs in the order of embeddings).
    """
    collection = helpers_resolvers.create_collection(session=session)
    embedding_model = helpers_resolvers.create_embedding_model(
        session=session,
        collection_id=collection.collection_id,
        embedding_dimension=3,
    )
    images = helpers_resolvers.create_samples_with_embeddings(
        session=session,
        collection_id=collection.collection_id,
        embedding_model_id=embedding_model.embedding_model_id,
        images_and_embeddings=[
            (ImageStub(path=f"sample_{i}.jpg"), embedding) for i, embedding in enumerate(embeddings)
        ],
    )
    return (
        collection.collection_id,
        embedding_model.embedding_model_id,
        [image.sample_id for image in images],
    )
