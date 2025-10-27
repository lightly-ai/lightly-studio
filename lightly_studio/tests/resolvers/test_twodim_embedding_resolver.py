from __future__ import annotations

import numpy as np
from pytest_mock import MockerFixture
from sqlmodel import Session

from lightly_studio.resolvers import twodim_embedding_resolver
from tests import helpers_resolvers
from tests.helpers_resolvers import (
    SampleImage,
)


def test__calculate_2d_embeddings__1_sample() -> None:
    embedding_values = [[0.1, 0.2, 0.3]]
    projected = twodim_embedding_resolver._calculate_2d_embeddings(embedding_values)
    assert projected == [(0.0, 0.0)]


def test__calculate_2d_embeddings__2_samples() -> None:
    embedding_values = [[0.1, 0.2, 0.3], [0.4, 0.5, 0.6]]
    projected = twodim_embedding_resolver._calculate_2d_embeddings(embedding_values)
    assert projected == [(0.0, 0.0), (1.0, 1.0)]


def test__get_twodim_embeddings__cache_hit(
    test_db: Session,
    mocker: MockerFixture,
) -> None:
    # Create dataset, embedding model, samples, and embeddings.
    dataset = helpers_resolvers.create_dataset(session=test_db, dataset_name="cache_hit_dataset")
    embedding_model = helpers_resolvers.create_embedding_model(
        session=test_db,
        dataset_id=dataset.dataset_id,
        embedding_dimension=3,
    )

    embeddings = [
        [0.1, 0.2, 0.3],
        [0.4, 0.5, 0.6],
    ]
    helpers_resolvers.create_samples_with_embeddings(
        db_session=test_db,
        dataset_id=dataset.dataset_id,
        embedding_model_id=embedding_model.embedding_model_id,
        images_and_embeddings=[
            (SampleImage(path="sample_1.jpg"), [0.1, 0.2, 0.3]),
            (SampleImage(path="sample_2.jpg"), [0.4, 0.5, 0.6]),
        ],
    )
    calculate_spy = mocker.spy(twodim_embedding_resolver, "_calculate_2d_embeddings")

    # First call - should call _calculate_2d_embeddings.
    x_first, y_first, sample_ids_first_call = twodim_embedding_resolver.get_twodim_embeddings(
        session=test_db,
        dataset_id=dataset.dataset_id,
        embedding_model_id=embedding_model.embedding_model_id,
    )
    calculate_spy.assert_called_once()

    assert x_first.shape == (2,)
    assert y_first.shape == (2,)
    assert len(sample_ids_first_call) == 2

    # Second call - should use cache, not call _calculate_2d_embeddings again.
    x_second, y_second, sample_ids_second_call = twodim_embedding_resolver.get_twodim_embeddings(
        session=test_db,
        dataset_id=dataset.dataset_id,
        embedding_model_id=embedding_model.embedding_model_id,
    )

    calculate_spy.assert_called_once()
    np.testing.assert_allclose(x_first, x_second)
    np.testing.assert_allclose(y_first, y_second)
    assert sample_ids_first_call == sample_ids_second_call

    # Third call after adding a sample without embeddings - should still use cache.
    helpers_resolvers.create_sample(
        session=test_db,
        dataset_id=dataset.dataset_id,
        file_path_abs="/sample_2.jpg",
    )
    x_third, y_third, sample_ids_third_call = twodim_embedding_resolver.get_twodim_embeddings(
        session=test_db,
        dataset_id=dataset.dataset_id,
        embedding_model_id=embedding_model.embedding_model_id,
    )
    calculate_spy.assert_called_once()
    np.testing.assert_allclose(x_first, x_third)
    np.testing.assert_allclose(y_first, y_third)
    assert sample_ids_first_call == sample_ids_third_call


def test__get_twodim_embeddings__recomputes_when_samples_change(
    test_db: Session,
    mocker: MockerFixture,
) -> None:
    # Create dataset, embedding model, samples, and embeddings.
    dataset = helpers_resolvers.create_dataset(session=test_db, dataset_name="cache_miss_dataset")
    embedding_model = helpers_resolvers.create_embedding_model(
        session=test_db,
        dataset_id=dataset.dataset_id,
        embedding_dimension=3,
    )

    first_sample = helpers_resolvers.create_sample(
        session=test_db,
        dataset_id=dataset.dataset_id,
        file_path_abs="/sample_0.jpg",
    )
    helpers_resolvers.create_sample_embedding(
        session=test_db,
        sample_id=first_sample.sample_id,
        embedding_model_id=embedding_model.embedding_model_id,
        embedding=[0.1, 0.1, 0.1],
    )

    calculate_spy = mocker.spy(twodim_embedding_resolver, "_calculate_2d_embeddings")

    # First call - should call _calculate_2d_embeddings.
    x_first, y_first, sample_ids_first = twodim_embedding_resolver.get_twodim_embeddings(
        session=test_db,
        dataset_id=dataset.dataset_id,
        embedding_model_id=embedding_model.embedding_model_id,
    )

    assert calculate_spy.call_count == 1
    assert x_first.shape == (1,)
    assert y_first.shape == (1,)
    assert len(sample_ids_first) == 1

    # Add another sample and embedding.
    second_sample = helpers_resolvers.create_sample(
        session=test_db,
        dataset_id=dataset.dataset_id,
        file_path_abs="/sample_1.jpg",
    )
    helpers_resolvers.create_sample_embedding(
        session=test_db,
        sample_id=second_sample.sample_id,
        embedding_model_id=embedding_model.embedding_model_id,
        embedding=[0.2, 0.2, 0.2],
    )

    # Second call - should recompute since samples changed.
    x_second, y_second, sample_ids_second = twodim_embedding_resolver.get_twodim_embeddings(
        session=test_db,
        dataset_id=dataset.dataset_id,
        embedding_model_id=embedding_model.embedding_model_id,
    )

    assert calculate_spy.call_count == 2
    assert x_second.shape == (2,)
    assert y_second.shape == (2,)
    assert len(sample_ids_second) == 2
